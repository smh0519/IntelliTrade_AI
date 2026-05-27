# quant_logic.py — N10-MEW 전략 핸들러

import pytz
from datetime import datetime
from config import (
    TIMEZONE, ORDER_TIMEOUT_MINUTES, UNFILLED_ORDER_ACTION,
    MOMENTUM_PERIOD_DAYS, TOP_N_PORTFOLIO, REBALANCE_EXIT_RANK,
    WEIGHT_PER_STOCK, PORTFOLIO_STOP_LOSS,
)
from utils.broker_api_client import BrokerAPIClient
from utils.logger import logger
from utils.universe import fetch_nasdaq100_universe
import utils.telegram_bot as telebot
import utils.supabase_client as supa
from utils.earnings import fetch_earnings_dates
from utils.market_filter import MarketRegime, update_regime, needs_second_emergency_exit, save_state
from rebalancer import N10MEWRebalancer, STRATEGY_TAG


class TradingStrategy:
    """
    N10-MEW (Nasdaq 10 Momentum Equal Weight) 전략 핸들러.

    - 월 첫 영업일: 정기 리밸런싱
    - 시장 국면 필터(안전벨트): NEUTRAL/CAUTION/EMERGENCY 단계별 방어
    - BULL 복귀 시 즉시 재진입 리밸런싱
    """

    def __init__(self, broker_client: BrokerAPIClient, user_id: str = ""):
        self.broker = broker_client
        self.user_id = user_id
        self.timezone = pytz.timezone(TIMEZONE)
        self.rebalancer = N10MEWRebalancer(broker_client, user_id=user_id)
        self.pending_orders: list = []
        self.full_ranking: list = []
        logger.info("TradingStrategy (N10-MEW) 초기화 완료.")

    # ------------------------------------------------------------------ #
    # 대시보드                                                             #
    # ------------------------------------------------------------------ #

    def render_dashboard(self, current_prices: dict):
        if not self.broker.is_simulation_mode:
            return

        import utils.mock_account as mock
        data = mock.get_virtual_balance()
        initial = data.get("initial_cash", 10000.0)
        cash = data.get("cash", 0.0)
        holdings = data.get("positions", {}).get(STRATEGY_TAG, {})

        total_value = cash
        lines = []

        for sym, info in holdings.items():
            qty = info.get("qty", 0.0)
            avg = info.get("avg_price", 0.0)
            cur_p = current_prices.get(sym, avg)
            value = qty * cur_p
            total_value += value

            pnl_pct = ((cur_p - avg) / avg * 100) if avg > 0 else 0.0
            weight = (value / total_value * 100) if total_value > 0 else 0.0
            indicator = "🟢" if pnl_pct > 0 else "🔴" if pnl_pct < 0 else "⚪"
            lines.append(
                f" └─ {sym:<6} | {qty:>7.3f}주 | 평단 ${avg:>8.2f} "
                f"| 현재 ${cur_p:>8.2f} | {pnl_pct:>+6.2f}% {indicator} | 비중 {weight:.1f}%"
            )

        total_pnl = ((total_value - initial) / initial * 100) if initial > 0 else 0.0
        now_str = datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M")

        logger.info("=" * 58)
        logger.info(f"📊 [N10-MEW 대시보드] {now_str} (NY)")
        logger.info(f"💰 총 자산: ${total_value:>10,.2f}  |  수익률: {total_pnl:>+6.2f}%")
        logger.info(f"💵 현금:   ${cash:>10,.2f}  |  보유 종목: {len(holdings)}개")
        if self.full_ranking:
            top5 = [r["ticker"] for r in self.full_ranking[:5]]
            logger.info(f"📈 모멘텀 Top 5: {top5}")
        logger.info("-" * 58)
        for line in lines:
            logger.info(line)
        logger.info("=" * 58)

        supa.push_portfolio_snapshot(
            cash=cash,
            total_value=total_value,
            initial_cash=initial,
            pnl_pct=total_pnl,
            positions=holdings,
            current_prices=current_prices,
            user_id=self.user_id,
        )
        if self.full_ranking:
            supa.push_momentum_rankings(self.full_ranking, list(holdings.keys()), user_id=self.user_id)

        earnings = fetch_earnings_dates(list(holdings.keys()))
        supa.push_earnings_calendar(earnings)

        if total_pnl <= PORTFOLIO_STOP_LOSS * 100:
            msg = (
                f"🚨 <b>[N10-MEW 포트폴리오 경고]</b>\n\n"
                f"전체 수익률이 {total_pnl:+.2f}%로 "
                f"경고선 ({PORTFOLIO_STOP_LOSS * 100:.0f}%)에 도달했습니다!\n"
                f"수동 점검이 필요합니다."
            )
            telebot.send_telegram_message(msg)

    # ------------------------------------------------------------------ #
    # 뉴스 점검                                                            #
    # ------------------------------------------------------------------ #

    def check_news_danger(self):
        """포트폴리오 보유 종목에 대해 AI 뉴스 악재 점검을 수행합니다."""
        import utils.ai_news_filter as ai

        portfolio = self.rebalancer.current_portfolio
        if not portfolio:
            logger.info("[AI News] 포트폴리오가 비어 있습니다. 뉴스 점검을 건너뜁니다.")
            return

        logger.info(f"🔍 [AI News] 포트폴리오 {len(portfolio)}개 종목 악재 점검 시작...")
        danger_list = [sym for sym in portfolio if ai.analyze_stock_news(sym)]

        if danger_list:
            msg = (
                f"⚠️ <b>[N10-MEW 뉴스 경보]</b>\n\n"
                f"다음 편입 종목에서 잠재적 악재가 감지되었습니다:\n"
                f"<b>{', '.join(danger_list)}</b>\n\n"
                f"다음 리밸런싱 시 자동 반영됩니다."
            )
            telebot.send_telegram_message(msg)

    # ------------------------------------------------------------------ #
    # 미체결 주문 관리                                                     #
    # ------------------------------------------------------------------ #

    def _check_pending_orders(self):
        if not self.pending_orders:
            return

        now = datetime.now()
        active = []
        for order in self.pending_orders:
            status_info = self.broker.get_order_status(order["order_id"])
            if not status_info:
                active.append(order)
                continue

            status = status_info.get("status")
            if status in ("filled", "canceled", "rejected"):
                continue

            elapsed_min = (now - order["time"]).total_seconds() / 60
            if elapsed_min >= ORDER_TIMEOUT_MINUTES:
                if UNFILLED_ORDER_ACTION == "cancel":
                    logger.warning(f"⚠️ [PendingOrders] 타임아웃 취소: {order['order_id']}")
                    self.broker.cancel_order(order["order_id"])
            else:
                active.append(order)

        self.pending_orders = active

    # ------------------------------------------------------------------ #
    # 국면 변경 알림                                                       #
    # ------------------------------------------------------------------ #

    def _notify_regime_change(self, prev: MarketRegime, new: MarketRegime) -> None:
        labels = {
            MarketRegime.BULL:      "🟢 BULL — 정상 운용",
            MarketRegime.NEUTRAL:   "🟡 NEUTRAL — 신규 매수 중단",
            MarketRegime.CAUTION:   "🔴 CAUTION — 탈락 매도만 허용",
            MarketRegime.EMERGENCY: "🚨 EMERGENCY — 긴급 청산",
        }
        actions = {
            MarketRegime.NEUTRAL:   "신규 매수 중단, 기존 포지션 유지",
            MarketRegime.CAUTION:   "탈락 종목 매도만 허용",
            MarketRegime.EMERGENCY: "즉시 70% 청산 시작, 2거래일 후 나머지 30% 청산",
            MarketRegime.BULL:      "정상 운용 재개 → 즉시 재진입 리밸런싱 실행",
        }
        msg = (
            f"📊 <b>[N10-MEW 시장 국면 변경]</b>\n\n"
            f"이전: {labels.get(prev, prev.value)}\n"
            f"현재: {labels.get(new, new.value)}\n\n"
            f"⚡ <b>조치:</b> {actions.get(new, '-')}"
        )
        telebot.send_telegram_message(msg)
        logger.info(f"[Strategy] 시장 국면 변경: {prev.value} → {new.value}")

    # ------------------------------------------------------------------ #
    # 현재가 일괄 조회                                                     #
    # ------------------------------------------------------------------ #

    def _fetch_prices(self, symbols: list) -> dict:
        prices = {}
        for sym in symbols:
            info = self.broker.get_current_price(sym)
            if info:
                prices[sym] = info.get("price")
        return prices

    # ------------------------------------------------------------------ #
    # 메인 전략 실행                                                       #
    # ------------------------------------------------------------------ #

    def execute_strategy(self):
        """
        매 실행 사이클:
          0. 시장 국면 업데이트 (안전벨트 체크)
          1. EMERGENCY 2차 청산 체크 (최우선)
          2. 모멘텀 랭킹 산출
          3. 현재가 조회 및 대시보드 출력
          4. 미체결 주문 처리
          5. EMERGENCY 1차 청산
          6. 리밸런싱 트리거 확인 (BULL 복귀 / 초기 / 월간)
        """
        import utils.screener as screener

        # 0. 시장 국면 업데이트
        prev_regime, new_regime, market_state = update_regime()
        if prev_regime != new_regime:
            self._notify_regime_change(prev_regime, new_regime)

        # 1. EMERGENCY 2차 청산 최우선 체크 (봇 재시작 후에도 이어서 처리)
        if new_regime == MarketRegime.EMERGENCY and needs_second_emergency_exit(market_state):
            logger.warning("[Strategy] EMERGENCY 2차 청산 (잔여 30%) 실행")
            holdings = self.rebalancer._get_holdings()
            prices = self._fetch_prices(list(holdings.keys()))
            self.rebalancer.execute_emergency_exit(prices, phase=2)
            market_state["emergency_phase"] = 2
            save_state(market_state)
            return

        # 2. 모멘텀 랭킹 산출
        self.full_ranking = screener.run_momentum_screener(
            fetch_nasdaq100_universe(),
            top_n=REBALANCE_EXIT_RANK + 2,
        )
        if not self.full_ranking:
            logger.error("🚫 [Strategy] 랭킹 산출 실패. 이번 사이클을 건너뜁니다.")
            return

        ranked_tickers = [r["ticker"] for r in self.full_ranking]

        # 3. 현재가 일괄 조회 (랭킹 종목 + 현재 보유 종목)
        holdings = self.rebalancer._get_holdings()
        all_symbols = list(set(ranked_tickers + list(holdings.keys())))
        current_prices = self._fetch_prices(all_symbols)

        # 4. 대시보드 출력 및 미체결 주문 처리
        self.render_dashboard(current_prices)
        self._check_pending_orders()

        # 5. EMERGENCY 1차 청산 (처음 EMERGENCY 진입 시)
        if new_regime == MarketRegime.EMERGENCY and prev_regime != MarketRegime.EMERGENCY:
            logger.warning("[Strategy] EMERGENCY 1차 청산 (70%) 실행")
            self.rebalancer.execute_emergency_exit(current_prices, phase=1)
            market_state["emergency_phase"] = 1
            market_state["emergency_first_exit_date"] = (
                datetime.now(self.timezone).date().isoformat()
            )
            save_state(market_state)
            return

        # 6. 리밸런싱 트리거 판단
        new_top10 = ranked_tickers[:TOP_N_PORTFOLIO]
        holdings = self.rebalancer._get_holdings()
        rebalanced = False

        # BULL 복귀 → 즉시 재진입 리밸런싱
        if prev_regime != MarketRegime.BULL and new_regime == MarketRegime.BULL:
            logger.info("[Strategy] BULL 복귀 → 즉시 재진입 리밸런싱")
            rebalanced = self.rebalancer.execute_rebalance(
                new_top10, current_prices,
                reason="시장 회복 재진입", regime=new_regime,
            )
            # 이번 달 정기 리밸런싱 중복 방지
            self.rebalancer.last_rebalance_month = datetime.now(self.timezone).month

        elif not holdings and not self.rebalancer.current_portfolio:
            if new_regime != MarketRegime.EMERGENCY:
                logger.info("[Strategy] 첫 실행 감지 — 초기 포트폴리오를 즉시 구성합니다.")
                rebalanced = self.rebalancer.execute_rebalance(
                    new_top10, current_prices,
                    reason="초기 포트폴리오 구성", force=True, regime=new_regime,
                )

        elif self.rebalancer.should_rebalance_monthly():
            logger.info("📅 [Strategy] 월간 정기 리밸런싱 트리거 발동!")
            rebalanced = self.rebalancer.execute_rebalance(
                new_top10, current_prices,
                reason="월간 정기 리밸런싱", regime=new_regime,
            )

        if rebalanced:
            updated_holdings = self.rebalancer._get_holdings()
            supa.push_momentum_rankings(
                self.full_ranking, list(updated_holdings.keys()), user_id=self.user_id
            )
