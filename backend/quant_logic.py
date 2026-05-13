# quant_logic.py — N10-MEW 전략 핸들러

import pytz
from datetime import datetime
from config import (
    UNIVERSE_TICKERS, TIMEZONE, ORDER_TIMEOUT_MINUTES, UNFILLED_ORDER_ACTION,
    MOMENTUM_PERIOD_DAYS, TOP_N_PORTFOLIO, REBALANCE_EXIT_RANK,
    WEIGHT_PER_STOCK, PORTFOLIO_STOP_LOSS,
)
from utils.broker_api_client import BrokerAPIClient
from utils.logger import logger
import utils.telegram_bot as telebot
import utils.supabase_client as supa
from rebalancer import N10MEWRebalancer, STRATEGY_TAG


class TradingStrategy:
    """
    N10-MEW (Nasdaq 10 Momentum Equal Weight) 전략 핸들러.

    - 월 첫 영업일 10:00 AM: 정기 리밸런싱
    - 보유 종목이 12위 밖으로 이탈: 즉시 교체 리밸런싱
    - 매 실행마다 모멘텀 랭킹 갱신 및 대시보드 출력
    """

    def __init__(self, broker_client: BrokerAPIClient):
        self.broker = broker_client
        self.timezone = pytz.timezone(TIMEZONE)
        self.rebalancer = N10MEWRebalancer(broker_client)
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
            logger.info(f"📈 모멘텀 Top 5: {self.full_ranking[:5]}")
        logger.info("-" * 58)
        for line in lines:
            logger.info(line)
        logger.info("=" * 58)

        # Supabase 스냅샷 push
        supa.push_portfolio_snapshot(
            cash=cash,
            total_value=total_value,
            initial_cash=initial,
            pnl_pct=total_pnl,
            positions=holdings,
            current_prices=current_prices,
        )
        if self.full_ranking:
            supa.push_momentum_rankings(self.full_ranking, list(holdings.keys()))

        # 전체 포트폴리오 손실 경고
        if total_pnl <= PORTFOLIO_STOP_LOSS * 100:
            msg = (
                f"🚨 <b>[N10-MEW 포트폴리오 경고]</b>\n\n"
                f"전체 수익률이 {total_pnl:+.2f}%로 "
                f"경고선 ({PORTFOLIO_STOP_LOSS * 100:.0f}%)에 도달했습니다!\n"
                f"수동 점검이 필요합니다."
            )
            telebot.send_telegram_message(msg)

    # ------------------------------------------------------------------ #
    # 뉴스 점검 (주간 1회 호출)                                            #
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
    # 메인 전략 실행                                                       #
    # ------------------------------------------------------------------ #

    def execute_strategy(self):
        """
        매 실행 사이클:
          1. 모멘텀 랭킹 산출
          2. 현재가 조회 및 대시보드 출력
          3. 미체결 주문 처리
          4. 리밸런싱 트리거 확인 (월간 / 랭킹 이탈)
        """
        import utils.screener as screener

        # 1. 최신 모멘텀 랭킹 산출 (Top 14: 포트폴리오 10 + 관찰 버퍼 4)
        self.full_ranking = screener.run_momentum_screener(
            UNIVERSE_TICKERS,
            top_n=REBALANCE_EXIT_RANK + 2,
        )

        if not self.full_ranking:
            logger.error("🚫 [Strategy] 랭킹 산출 실패. 이번 사이클을 건너뜁니다.")
            return

        # 2. 현재가 일괄 조회
        current_prices = {}
        for sym in self.full_ranking:
            price_info = self.broker.get_current_price(sym)
            if price_info:
                current_prices[sym] = price_info.get("price")

        # 3. 대시보드 출력
        self.render_dashboard(current_prices)

        # 4. 미체결 주문 처리
        self._check_pending_orders()

        # 5. 리밸런싱 트리거 판단
        new_top10 = self.full_ranking[:TOP_N_PORTFOLIO]
        holdings = self.rebalancer._get_holdings()

        if not holdings and not self.rebalancer.current_portfolio:
            # 첫 실행: 포지션이 없으면 즉시 초기 포트폴리오 구성 (시간 제한 없음)
            logger.info("🆕 [Strategy] 첫 실행 감지 — 초기 포트폴리오를 즉시 구성합니다.")
            self.rebalancer.execute_rebalance(
                new_top10, current_prices, reason="초기 포트폴리오 구성", force=True
            )

        elif self.rebalancer.should_rebalance_monthly():
            logger.info("📅 [Strategy] 월간 정기 리밸런싱 트리거 발동!")
            self.rebalancer.execute_rebalance(
                new_top10, current_prices, reason="월간 정기 리밸런싱"
            )

        elif self.rebalancer.current_portfolio:
            drifted = self.rebalancer.check_rank_drift(self.full_ranking)
            if drifted:
                reason = f"랭킹 이탈 교체 ({', '.join(drifted)} → {REBALANCE_EXIT_RANK}위 밖)"
                logger.warning(f"⚠️ [Strategy] {reason}")
                self.rebalancer.execute_rebalance(
                    new_top10, current_prices, reason=reason
                )
