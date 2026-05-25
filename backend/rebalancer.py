# rebalancer.py — N10-MEW 월간 리밸런싱 엔진

import pytz
from datetime import datetime, date
from utils.logger import logger
import utils.telegram_bot as telebot
import utils.mock_account as mock
import utils.supabase_client as supa
import utils.withdrawal as withdrawal
from config import (
    WEIGHT_PER_STOCK, REBALANCE_THRESHOLD, REBALANCE_EXIT_RANK,
    ORDER_TIMEOUT_MINUTES, UNFILLED_ORDER_ACTION,
    TIMEZONE, TRADE_END_TIME, REBALANCE_EXECUTION_TIME,
)

STRATEGY_TAG = "N10_MEW"


class N10MEWRebalancer:
    """
    N10-MEW 전략 리밸런싱 엔진.

    - 월 첫 영업일: 정기 리밸런싱
    - 보유 종목이 12위 밖으로 이탈: 즉시 교체
    """

    def __init__(self, broker, user_id: str = ""):
        self.broker = broker
        self.user_id = user_id
        self.timezone = pytz.timezone(TIMEZONE)
        self.last_rebalance_month: int | None = None
        self.current_portfolio: list = []   # 현재 편입된 Top 10 종목
        self.full_ranking: list = []        # 최신 12위 랭킹 (이탈 감지용)

    # ------------------------------------------------------------------ #
    # 날짜 유틸                                                            #
    # ------------------------------------------------------------------ #

    def _first_trading_day_of_month(self, year: int, month: int) -> date:
        """해당 월의 첫 영업일을 반환합니다 (토→월요일, 일→월요일)."""
        first = date(year, month, 1)
        weekday = first.weekday()  # 0=Mon … 6=Sun
        if weekday == 5:           # 토요일 → 월요일
            first = date(year, month, 3)
        elif weekday == 6:         # 일요일 → 월요일
            first = date(year, month, 2)
        return first

    def is_first_trading_day_of_month(self) -> bool:
        today = datetime.now(self.timezone).date()
        return today == self._first_trading_day_of_month(today.year, today.month)

    # ------------------------------------------------------------------ #
    # 트리거 판단                                                          #
    # ------------------------------------------------------------------ #

    def should_rebalance_monthly(self) -> bool:
        """이번 달 정기 리밸런싱을 아직 실행하지 않았고, 오늘이 첫 영업일인지 확인합니다."""
        today = datetime.now(self.timezone).date()
        already_done = (self.last_rebalance_month == today.month)
        return self.is_first_trading_day_of_month() and not already_done

    def check_rank_drift(self, full_ranking: list) -> list:
        """현재 포트폴리오 중 12위 밖으로 이탈한 종목 목록을 반환합니다."""
        watch_zone = set(full_ranking[:REBALANCE_EXIT_RANK])
        return [t for t in self.current_portfolio if t not in watch_zone]

    # ------------------------------------------------------------------ #
    # 내부 헬퍼                                                            #
    # ------------------------------------------------------------------ #

    def _is_execution_window(self) -> bool:
        """집행 가능 시간대(REBALANCE_EXECUTION_TIME ~ 장 마감 전)인지 확인합니다."""
        current_time = datetime.now(self.timezone).strftime("%H:%M")
        return REBALANCE_EXECUTION_TIME <= current_time <= TRADE_END_TIME

    def _get_holdings(self) -> dict:
        """현재 N10_MEW 포지션 반환 {ticker: {"qty": float, "avg_price": float}}"""
        if self.broker.is_simulation_mode:
            data = mock.get_virtual_balance()
            return data.get("positions", {}).get(STRATEGY_TAG, {})
        return {}  # 실제 브로커 연동은 broker 확장 시 구현

    def _get_total_value(self, current_prices: dict) -> float:
        """총 포트폴리오 가치 (현금 + 보유 주식 평가액)"""
        if self.broker.is_simulation_mode:
            data = mock.get_virtual_balance()
            cash = data.get("cash", 0.0)
            holdings = data.get("positions", {}).get(STRATEGY_TAG, {})
        else:
            acc = self.broker.get_account_balance() or {}
            cash = acc.get("cash", 0.0)
            holdings = {}

        total = cash
        for ticker, info in holdings.items():
            price = current_prices.get(ticker, info.get("avg_price", 0))
            total += info.get("qty", 0) * price
        return total

    def _place_sell(self, ticker: str, qty: float) -> float | None:
        """매도 주문 실행 후 체결가 반환. 실패 시 None."""
        res = self.broker.place_sell_order(ticker, qty, strategy_tag=STRATEGY_TAG)
        if res and res.get("status") == "filled":
            price = res.get("executed_price")
            supa.push_trade("sell", ticker, qty, price, STRATEGY_TAG, self.user_id)
            return price
        return None

    def _place_buy(self, ticker: str, qty: float) -> float | None:
        """매수 주문 실행 후 체결가 반환. 실패 시 None."""
        res = self.broker.place_buy_order(ticker, qty, strategy_tag=STRATEGY_TAG)
        if res and res.get("status") == "filled":
            price = res.get("executed_price")
            supa.push_trade("buy", ticker, qty, price, STRATEGY_TAG, self.user_id)
            return price
        return None

    # ------------------------------------------------------------------ #
    # 리밸런싱 집행                                                        #
    # ------------------------------------------------------------------ #

    def execute_rebalance(
        self, new_top10: list, current_prices: dict,
        reason: str = "월간 정기 리밸런싱", force: bool = False
    ) -> bool:
        """
        리밸런싱 3단계:
          1. 탈락 종목 전량 매도  (현금 확보)
          2. 잔류 종목 과비중 매도 (비중 정규화)
          3. 신규/과소비중 종목 매수
        force=True 이면 집행 시간 제한을 무시합니다 (초기 포트폴리오 구성 시).
        """
        if not force and not self._is_execution_window():
            logger.info(
                f"⏳ [Rebalancer] 집행 가능 시간이 아닙니다 "
                f"({REBALANCE_EXECUTION_TIME} 이후부터 가능)."
            )
            return False

        logger.info(f"🔄 [Rebalancer] 리밸런싱 시작 — 사유: {reason}")
        logger.info(f"🎯 [Rebalancer] 목표 포트폴리오: {new_top10}")

        total_value = self._get_total_value(current_prices)

        # 출금 예약 확인 — 예약액만큼 투자 대상 총액에서 제외
        withdrawal_amount = withdrawal.get_reservation() or 0.0
        if withdrawal_amount > 0:
            if withdrawal_amount >= total_value:
                logger.warning(
                    f"⚠️ [Rebalancer] 출금 예약액(${withdrawal_amount:.2f})이 "
                    f"총 자산(${total_value:.2f}) 이상 — 예약 무시"
                )
                withdrawal_amount = 0.0
            else:
                logger.info(
                    f"💸 [Rebalancer] 출금 예약 감지: ${withdrawal_amount:.2f} "
                    f"(총 자산 ${total_value:.2f}에서 제외)"
                )

        investable = total_value - withdrawal_amount
        target_per_stock = investable * WEIGHT_PER_STOCK

        sold_log: list[str] = []
        bought_log: list[str] = []

        # ── 1단계: 탈락 종목 전량 매도 ──────────────────────────────────
        holdings = self._get_holdings()
        for ticker, info in list(holdings.items()):
            if ticker not in new_top10:
                qty = info.get("qty", 0)
                if qty <= 0:
                    continue
                logger.info(f"📤 [Rebalancer] 탈락 매도: {ticker} {qty:g}주")
                exec_price = self._place_sell(ticker, qty)
                if exec_price:
                    sold_log.append(f"{ticker} @ ${exec_price:.2f}")

        # ── 2단계: 잔류 종목 과비중 조정 매도 ──────────────────────────
        holdings = self._get_holdings()
        for ticker in new_top10:
            if ticker not in holdings:
                continue
            cur_price = current_prices.get(ticker)
            if not cur_price:
                continue
            cur_value = holdings[ticker].get("qty", 0) * cur_price
            drift = (cur_value - target_per_stock) / target_per_stock

            if drift > REBALANCE_THRESHOLD:
                excess_value = cur_value - target_per_stock
                sell_qty = round(excess_value / cur_price, 4)
                if sell_qty > 0:
                    logger.info(
                        f"⚖️ [Rebalancer] 과비중 조정 매도: {ticker} "
                        f"{sell_qty:g}주 (초과 {drift * 100:.1f}%)"
                    )
                    self._place_sell(ticker, sell_qty)

        # ── 3단계: 신규 편입 및 과소비중 매수 ──────────────────────────
        import math

        holdings = self._get_holdings()

        # 1차 패스: 매수 필요 종목 수집 (현재가 없는 종목 선제 제외)
        buys_needed: list[tuple[str, float, float]] = []  # (ticker, cur_price, cur_value)
        for ticker in new_top10:
            cur_price = current_prices.get(ticker)
            if not cur_price:
                logger.warning(f"⚠️ [Rebalancer] {ticker} 현재가 없음, 매수 건너뜁니다.")
                continue
            cur_value = holdings.get(ticker, {}).get("qty", 0) * cur_price
            drift = (target_per_stock - cur_value) / target_per_stock
            if drift > REBALANCE_THRESHOLD:
                buys_needed.append((ticker, cur_price, cur_value))

        # 2차 패스: 매수 실행 — 마지막 종목은 잔여 현금 전액 투자
        for i, (ticker, cur_price, cur_value) in enumerate(buys_needed):
            is_last = (i == len(buys_needed) - 1)

            if self.broker.is_simulation_mode:
                available_cash = mock.get_virtual_balance().get("cash", 0.0)
            else:
                acc = self.broker.get_account_balance() or {}
                available_cash = acc.get("cash", 0.0)

            usable_cash = available_cash / 1.0005

            if is_last:
                # 마지막 종목: 남은 현금 전액 사용 (target 상한 제거)
                buy_value = usable_cash
            else:
                buy_value = min(target_per_stock - cur_value, usable_cash)

            if buy_value <= 0:
                logger.warning(f"⚠️ [Rebalancer] {ticker} 매수 불가 (가용현금 없음)")
                continue

            # 소수점 매수: 항상 내림(floor)으로 오버스펜드 방지
            buy_qty = math.floor(buy_value / cur_price * 10000) / 10000
            if buy_qty <= 0:
                continue

            action = "신규 편입" if cur_value == 0 else "비중 보강"
            logger.info(
                f"📥 [Rebalancer] {action} 매수: {ticker} "
                f"{buy_qty:g}주 @ ${cur_price:.2f}"
                + (" [잔여현금 전액]" if is_last else "")
            )
            exec_price = self._place_buy(ticker, buy_qty)
            if exec_price:
                bought_log.append(f"{ticker} @ ${exec_price:.2f}")

        # ── 완료 처리 ────────────────────────────────────────────────────
        today = datetime.now(self.timezone).date()
        self.last_rebalance_month = today.month
        self.current_portfolio = new_top10[:]

        # 출금 예약 이행 완료 → 예약 초기화
        if withdrawal_amount > 0:
            withdrawal.clear_reservation()

        portfolio_lines = "\n".join(
            [f"  {i + 1:>2}. {t}" for i, t in enumerate(new_top10)]
        )
        msg = (
            f"🔄 <b>[N10-MEW 리밸런싱 완료]</b>\n\n"
            f"📅 날짜: {today}\n"
            f"📋 사유: {reason}\n\n"
            f"🎯 <b>새 포트폴리오 (Top 10):</b>\n{portfolio_lines}"
        )
        if sold_log:
            msg += f"\n\n📤 <b>매도:</b> {', '.join(sold_log)}"
        if bought_log:
            msg += f"\n📥 <b>매수:</b> {', '.join(bought_log)}"
        if withdrawal_amount > 0:
            msg += f"\n💸 <b>출금 예약 이행:</b> ${withdrawal_amount:,.2f} 현금 보유"

        telebot.send_telegram_message(msg)
        supa.push_rebalance_log(
            reason=reason,
            new_portfolio=new_top10,
            sold_tickers=[s.split(" @")[0] for s in sold_log],
            bought_tickers=[b.split(" @")[0] for b in bought_log],
            user_id=self.user_id,
        )
        logger.info("✅ [Rebalancer] 리밸런싱 집행 완료.")
        return True
