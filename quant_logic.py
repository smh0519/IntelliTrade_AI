# quant_logic.py
import time
import pytz
from datetime import datetime, timedelta
from config import (
    TARGET_STOCK_SYMBOL, MIN_CASH_BALANCE, TRADE_START_TIME, TRADE_END_TIME, 
    TIMEZONE, ORDER_TIMEOUT_MINUTES, UNFILLED_ORDER_ACTION, MAX_DAILY_BUYS_PER_SYMBOL,
    TRADE_AMOUNT_STRAT_A, TRADE_AMOUNT_STRAT_B, TRADE_AMOUNT_STRAT_C,
    REQUIRE_VOLUME_SPIKE_MULTI, TIMECUT_HOUR, TIMECUT_MINUTE, SP500_SYMBOL
)
from utils.broker_api_client import BrokerAPIClient
from utils.logger import logger
import utils.market_data as md
import utils.indicators as ind

class TradingStrategy:
    """
    3가지 하이브리드 전략을 동시 가동하는 멀티 전략 라우터입니다.
    """
    def __init__(self, broker_client: BrokerAPIClient):
        self.broker = broker_client
        self.timezone = pytz.timezone(TIMEZONE)
        self.pending_orders = [] 
        # 일일 매수 제한 (전체 종목 통합 또는 종목별, 여기서는 심볼별)
        self.daily_buy_counts = {} 
        self.last_trading_date = None
        
        # [핵심] 멀티 전략 간 주식 수량 격리 장부 (Position Partitioning)
        self.positions = {
            "STRAT_A": 0.0,
            "STRAT_B": 0.0,
            "STRAT_C": 0.0
        }
        logger.info("TradingStrategy (Multi-Strategy Router) 초기화 완료.")

    def _check_pending_orders(self):
        """미체결 주문들의 타임아웃을 관리합니다."""
        if not self.pending_orders: return
        now = datetime.now()
        active_orders = []

        for p_order in self.pending_orders:
            order_id = p_order['order_id']
            order_time = p_order['time']
            strat_tag = p_order.get('tag')

            status_info = self.broker.get_order_status(order_id)
            if not status_info:
                active_orders.append(p_order)
                continue

            status = status_info.get("status")
            if status == "filled":
                logger.info(f"✅ [{strat_tag}] 대기 주문 체결 확인! (ID: {order_id})")
                continue 
            elif status in ["canceled", "rejected"]:
                logger.warning(f"❌ [{strat_tag}] 주문 취소/거절 됨. (ID: {order_id})")
                continue

            elapsed_minutes = (now - order_time).total_seconds() / 60.0
            if elapsed_minutes >= ORDER_TIMEOUT_MINUTES:
                if UNFILLED_ORDER_ACTION == "cancel":
                    logger.critical(f"⚠️ [{strat_tag}] 타임아웃 강제 취소 시도. (ID: {order_id})")
                    if self.broker.cancel_order(order_id):
                        logger.info(f"타임아웃 락업 해제 완료.")
                    else:
                        active_orders.append(p_order)
            else:
                active_orders.append(p_order)

        self.pending_orders = active_orders

    def _check_and_reset_daily_counts(self):
        now = datetime.now(self.timezone)
        current_date = now.date()
        if self.last_trading_date != current_date:
            logger.info("📅 [시스템] 새로운 거래일. 일일 거래 횟수 추적 초기화.")
            self.daily_buy_counts = {}
            self.last_trading_date = current_date

    def _is_trading_time(self):
        now = datetime.now(self.timezone)
        current_time_str = now.strftime("%H:%M")
        return TRADE_START_TIME <= current_time_str <= TRADE_END_TIME

    def _execute_buy(self, strat_tag: str, amount_usd: float, current_price: float):
        """특정 전략(Tag)의 예산으로 매수를 실행하고 내부 장부에 기록합니다."""
        buys_today = self.daily_buy_counts.get(TARGET_STOCK_SYMBOL, 0)
        if buys_today >= MAX_DAILY_BUYS_PER_SYMBOL:
            logger.warning(f"🚫 [{strat_tag} 매수 보류] 일일 허용 횟수({MAX_DAILY_BUYS_PER_SYMBOL}) 소진.")
            return

        quantity = round(amount_usd / current_price, 2)
        if quantity <= 0: return

        logger.info(f"🚀 [{strat_tag}] 타점 도달! {quantity}주 매수 진입 시도.")
        self.daily_buy_counts[TARGET_STOCK_SYMBOL] = buys_today + 1
        
        ord_res = self.broker.place_buy_order(TARGET_STOCK_SYMBOL, quantity)
        
        if ord_res:
            order_id = ord_res.get('order_id')
            if ord_res.get('status') == "filled":
                logger.info(f"✅ [{strat_tag}] 즉시 체결! 평균가: {ord_res.get('executed_price')}")
                self.positions[strat_tag] += quantity
            else:
                logger.warning(f"⏳ [{strat_tag}] 미체결 대기열 진입. (ID: {order_id})")
                self.pending_orders.append({"order_id": order_id, "time": datetime.now(), "tag": strat_tag})
                # 추후 체결 폴링 시 positions를 올려주어야 하나, 여기서는 심플하게 대기.
        else:
            logger.error(f"❌ [{strat_tag}] 매수 주문 전송 자체 실패.")
            self.daily_buy_counts[TARGET_STOCK_SYMBOL] -= 1

    def evaluate_strategy_A(self, df, current_price, cash):
        """전략 A: 순수 변동성 돌파"""
        if cash < TRADE_AMOUNT_STRAT_A: return
        target_price = ind.calculate_breakout_target(df, 0.5)
        if target_price and current_price >= target_price:
            self._execute_buy("STRAT_A", TRADE_AMOUNT_STRAT_A, current_price)

    def evaluate_strategy_B(self, df, current_price, cash):
        """전략 B: 변동성 돌파 + 추세(MA) 필터 + 거래량 스파이크 필터"""
        if cash < TRADE_AMOUNT_STRAT_B: return
        
        target_price = ind.calculate_breakout_target(df, 0.5)
        is_breakout = target_price and current_price >= target_price
        is_uptrend = ind.calculate_ma_condition(df, 20)
        is_vol_spike = ind.check_volume_spike(df, REQUIRE_VOLUME_SPIKE_MULTI)
        
        if is_breakout and is_uptrend and is_vol_spike:
            self._execute_buy("STRAT_B", TRADE_AMOUNT_STRAT_B, current_price)

    def evaluate_strategy_C(self, df, bm_df, current_price, cash):
        """전략 C: 낙폭 과대 스윙 (대세 하락장 접근 금지 필터 결합)"""
        if cash < TRADE_AMOUNT_STRAT_C: return
        
        # 마크로 필터 (대세 하락장 락온)
        if not ind.is_macro_trend_bullish(bm_df, 200):
            return # 스킵
            
        # 볼린저 밴드 + RSI 검사
        if ind.check_bollinger_rsi_condition(df):
            self._execute_buy("STRAT_C", TRADE_AMOUNT_STRAT_C, current_price)

    def process_timecuts(self):
        """시간 필터: 오버나이팅 방지를 위한 전략 A의 당일 강제 청산"""
        now = datetime.now(self.timezone)
        if now.hour == TIMECUT_HOUR and now.minute >= TIMECUT_MINUTE:
            qty = self.positions["STRAT_A"]
            if qty > 0:
                logger.critical(f"⏰ [Timecut] 전략 A 오버나잇 방지 강제 전량 매도! ({qty}주)")
                res = self.broker.place_sell_order(TARGET_STOCK_SYMBOL, qty)
                if res:
                    self.positions["STRAT_A"] = 0.0

    def execute_strategy(self):
        logger.info("====================================")
        logger.info("--- 🤖 멀티 전략 토너먼트 실행 ---")
        
        self._check_pending_orders()
        self._check_and_reset_daily_counts()
        self.process_timecuts() # 타임컷 시간인지 가장 먼저 확인

        if not self._is_trading_time():
            return

        acc = self.broker.get_account_balance()
        if not acc: return
        cash = acc.get("cash", 0)

        price_info = self.broker.get_current_price(TARGET_STOCK_SYMBOL)
        if not price_info: return
        current_price = price_info.get("price")
        
        # 1. API 비용 및 과부하를 줄이기 위해 과거 데이터는 1번만 일괄 다운로드
        df = md.fetch_historical_data(TARGET_STOCK_SYMBOL, period="60d")
        bm_df = md.fetch_benchmark_data(SP500_SYMBOL, period="250d")
        
        if df is None or bm_df is None:
            logger.error("시장 데이터 페치 실패. 전략 평가 스킵.")
            return

        # 2. 3개의 전략 엔진에 동시 데이터 투입 (병렬 검사)
        logger.debug(f"[Router] {TARGET_STOCK_SYMBOL} 현재가: {current_price} | A/B/C 전략 평가 시작...")
        self.evaluate_strategy_A(df, current_price, cash)
        self.evaluate_strategy_B(df, current_price, cash)
        self.evaluate_strategy_C(df, bm_df, current_price, cash)
        
        logger.info("====================================")
