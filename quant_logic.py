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
    3가지 하이브리드 전략을 동시 가동하는 멀티 전략 라우터 및 대시보드 시스템입니다.
    """
    def __init__(self, broker_client: BrokerAPIClient):
        self.broker = broker_client
        self.timezone = pytz.timezone(TIMEZONE)
        self.pending_orders = [] 
        self.daily_buy_counts = {} 
        self.last_trading_date = None
        
        # 내부 메모리 장부 (라이브 환경 대비용)
        self.positions = {
            "STRAT_A": {},
            "STRAT_B": {},
            "STRAT_C": {}
        }
        logger.info("TradingStrategy (Multi-Strategy Router) 초기화 완료.")

    def render_dashboard(self, current_prices_dict):
        """콘솔용 실시간 포트폴리오 대시보드를 렌더링합니다."""
        if not self.broker.is_simulation_mode:
            logger.info("--- 라이브 모드 대시보드 생략 (추후 DB 연동 예정) ---")
            return
            
        import utils.mock_account as mock
        data = mock.get_virtual_balance()
        initial = data.get("initial_cash", 10000.0)
        cash = data["cash"]
        
        total_value = cash
        print_lines = []
        
        # 전략별 순회
        for strat, symbols_dict in data["positions"].items():
            strat_display_name = strat
            if strat == "STRAT_A": strat_display_name = "STRAT_A (돌파)"
            if strat == "STRAT_B": strat_display_name = "STRAT_B (하이브리드)"
            if strat == "STRAT_C": strat_display_name = "STRAT_C (스윙)"
            
            print_lines.append(f"[{strat_display_name}]")
            if not symbols_dict:
                print_lines.append(" └─ ⚪ 대기 중 (포지션 없음)")
                continue
                
            for sym, info in symbols_dict.items():
                qty = info.get("qty", 0.0)
                avg = info.get("avg_price", 0.0)
                # 현재가 조회 (페치 실패 시 평단가로 갈음)
                cur_p = current_prices_dict.get(sym, avg)
                
                value = qty * cur_p
                total_value += value
                
                if avg > 0:
                    pnl_pct = ((cur_p - avg) / avg) * 100
                else: 
                    pnl_pct = 0.0
                    
                color = "🟢" if pnl_pct > 0 else "🔴" if pnl_pct < 0 else "⚪"
                print_lines.append(f" └─ {sym} : 보유 {qty:g}주 | 평단 ${avg:.2f} | 현재 ${cur_p:.2f} | 수익 {pnl_pct:+.2f}% {color}")
                
        total_pnl_pct = ((total_value - initial) / initial) * 100
        
        logger.info("==================================================")
        logger.info(f"📊 [실시간 통합 대시보드] - {datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M')} (NY)")
        logger.info("--------------------------------------------------")
        logger.info(f"💰 총 자본금: ${total_value:,.2f} (초기 ${initial:,.2f})")
        logger.info(f"📈 총 수익률: {total_pnl_pct:+.2f}%")
        logger.info(f"💵 보유 현금: ${cash:,.2f}")
        logger.info("--------------------------------------------------")
        for line in print_lines:
            logger.info(line)
        logger.info("==================================================")

    def _check_pending_orders(self):
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
        is_trading = TRADE_START_TIME <= current_time_str <= TRADE_END_TIME
        if not is_trading:
            # 잦은 알림 방지, 생략 가능
            pass
        return is_trading

    def _execute_buy(self, strat_tag: str, amount_usd: float, current_price: float):
        buys_today = self.daily_buy_counts.get(TARGET_STOCK_SYMBOL, 0)
        if buys_today >= MAX_DAILY_BUYS_PER_SYMBOL:
            logger.debug(f"[{strat_tag}] 일일 한도 소진 패스.")
            return

        quantity = round(amount_usd / current_price, 2)
        if quantity <= 0: return

        logger.info(f"🚀 [{strat_tag}] 타점 도달! {quantity}주 매수 진입 시도.")
        self.daily_buy_counts[TARGET_STOCK_SYMBOL] = buys_today + 1
        
        ord_res = self.broker.place_buy_order(TARGET_STOCK_SYMBOL, quantity, strategy_tag=strat_tag)
        
        if ord_res:
            order_id = ord_res.get('order_id')
            if ord_res.get('status') == "filled":
                logger.info(f"✅ [{strat_tag}] 즉시 체결! 평균가: {ord_res.get('executed_price')}")
                val = self.positions[strat_tag].get(TARGET_STOCK_SYMBOL, 0.0)
                self.positions[strat_tag][TARGET_STOCK_SYMBOL] = val + quantity
            else:
                logger.warning(f"⏳ [{strat_tag}] 미체결 대기열 진입. (ID: {order_id})")
                self.pending_orders.append({"order_id": order_id, "time": datetime.now(), "tag": strat_tag})
        else:
            logger.error(f"❌ [{strat_tag}] 매수 주문 전송 자체 실패.")
            self.daily_buy_counts[TARGET_STOCK_SYMBOL] -= 1

    def evaluate_strategy_A(self, df, current_price, cash):
        if cash < TRADE_AMOUNT_STRAT_A: return
        target_price = ind.calculate_breakout_target(df, 0.5)
        if target_price and current_price >= target_price:
            self._execute_buy("STRAT_A", TRADE_AMOUNT_STRAT_A, current_price)

    def evaluate_strategy_B(self, df, current_price, cash):
        if cash < TRADE_AMOUNT_STRAT_B: return
        target_price = ind.calculate_breakout_target(df, 0.5)
        is_breakout = target_price and current_price >= target_price
        is_uptrend = ind.calculate_ma_condition(df, 20)
        is_vol_spike = ind.check_volume_spike(df, REQUIRE_VOLUME_SPIKE_MULTI)
        if is_breakout and is_uptrend and is_vol_spike:
            self._execute_buy("STRAT_B", TRADE_AMOUNT_STRAT_B, current_price)

    def evaluate_strategy_C(self, df, bm_df, current_price, cash):
        if cash < TRADE_AMOUNT_STRAT_C: return
        if not ind.is_macro_trend_bullish(bm_df, 200): return
        if ind.check_bollinger_rsi_condition(df):
            self._execute_buy("STRAT_C", TRADE_AMOUNT_STRAT_C, current_price)

    def process_timecuts(self):
        now = datetime.now(self.timezone)
        if now.hour == TIMECUT_HOUR and now.minute >= TIMECUT_MINUTE:
            # 페이퍼 트레이딩 장부 직접 강제 청산
            if self.broker.is_simulation_mode:
                import utils.mock_account as mock
                data = mock.get_virtual_balance()
                strat_a_holdings = data["positions"].get("STRAT_A", {})
                for sym, info in strat_a_holdings.items():
                    qty = info.get("qty", 0)
                    if qty > 0:
                        logger.critical(f"⏰ [Timecut] STRAT_A 오버나잇 금지 강제 청산: {sym} {qty}주")
                        self.broker.place_sell_order(sym, qty, strategy_tag="STRAT_A")
            else:
                qty = self.positions["STRAT_A"].get(TARGET_STOCK_SYMBOL, 0)
                if qty > 0:
                    self.broker.place_sell_order(TARGET_STOCK_SYMBOL, qty, strategy_tag="STRAT_A")
                    self.positions["STRAT_A"][TARGET_STOCK_SYMBOL] = 0

    def execute_strategy(self):
        # 1. 봇을 켰을 때, 거래시간이 아니더라도 대시보드를 위해 현재가를 한 번 체크합니다.
        price_info = self.broker.get_current_price(TARGET_STOCK_SYMBOL)
        if not price_info: return
        current_price = price_info.get("price")
        
        # 최상단에 대시보드 렌더링
        self.render_dashboard({TARGET_STOCK_SYMBOL: current_price})
        
        self._check_pending_orders()
        self._check_and_reset_daily_counts()
        self.process_timecuts() 

        if not self._is_trading_time():
            return

        acc = self.broker.get_account_balance()
        if not acc: return
        cash = acc.get("cash", 0)

        df = md.fetch_historical_data(TARGET_STOCK_SYMBOL, period="60d")
        bm_df = md.fetch_benchmark_data(SP500_SYMBOL, period="250d")
        
        if df is None or bm_df is None: return

        self.evaluate_strategy_A(df, current_price, cash)
        self.evaluate_strategy_B(df, current_price, cash)
        self.evaluate_strategy_C(df, bm_df, current_price, cash)
