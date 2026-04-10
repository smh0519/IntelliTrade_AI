# quant_logic.py
import time
import pytz
from datetime import datetime, timedelta
from config import (
    UNIVERSE_TICKERS, MIN_CASH_BALANCE, TRADE_START_TIME, TRADE_END_TIME, 
    TIMEZONE, ORDER_TIMEOUT_MINUTES, UNFILLED_ORDER_ACTION, MAX_DAILY_BUYS_PER_SYMBOL,
    TRADE_AMOUNT_STRAT_A, TRADE_AMOUNT_STRAT_B, TRADE_AMOUNT_STRAT_C,
    REQUIRE_VOLUME_SPIKE_MULTI, TIMECUT_HOUR, TIMECUT_MINUTE, SP500_SYMBOL,
    STRAT_A_TP, STRAT_A_SL, STRAT_B_TP, STRAT_B_SL, STRAT_C_TP, STRAT_C_SL
)
from utils.broker_api_client import BrokerAPIClient
from utils.logger import logger
import utils.telegram_bot as telebot
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
        
        # 오늘의 스캔 타겟 리스트
        self.active_targets = []
        
        # 지능형 다중 매수 방어 로직용 메모리
        self.last_buy_time = {} # {'STRAT_tag_SYM': datetime}
        
        # 내부 메모리 장부 (라이브 환경 대비용)
        self.positions = {
            "STRAT_A": {},
            "STRAT_B": {},
            "STRAT_C": {}
        }
        # AI 뉴스 폭락 방어막 (종목별)
        self.news_danger_status = {}
        
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
        logger.info(f"🎯 오늘의 감시 타겟: {self.active_targets}")
        logger.info("--------------------------------------------------")
        logger.info(f"💰 총 자본금: ${total_value:,.2f} (초기 ${initial:,.2f})")
        logger.info(f"📈 총 수익률: {total_pnl_pct:+.2f}%")
        logger.info(f"💵 보유 현금: ${cash:,.2f}")
        logger.info("--------------------------------------------------")
        
        # AI 레이더 경고등 렌더링
        danger_syms = [s for s, is_danger in self.news_danger_status.items() if is_danger]
        if danger_syms:
            logger.info(f"🚨 [AI 뉴스 마크맨] : {danger_syms} 치명적 악재 감지로 매수 통제 중 🚨")
            logger.info("--------------------------------------------------")
            
        for line in print_lines:
            logger.info(line)
        logger.info("==================================================")

    def check_news_danger(self):
        """매일 선정된 타겟들의 최신 뉴스를 긁어와 제미나이에게 판별을 요청합니다."""
        import utils.ai_news_filter as ai
        for sym in self.active_targets:
            logger.info(f"🔍 [AI News] {sym} 최신 악재 점검을 시작합니다...")
            result = ai.analyze_stock_news(sym)
            
            # 최초로 감지되었을 때 긴급 푸시
            if result and not self.news_danger_status.get(sym, False):
                msg = f"🚨 <b>[IntelliTrade 긴급 보고]</b>\n\n<b>{sym}</b> 종목에 대한 치명적인 뉴스 악재가 AI에 의해 감지되었습니다!\n오늘 해당 종목 매수를 전면 차단합니다."
                telebot.send_telegram_message(msg)
                
            self.news_danger_status[sym] = result

    def _check_pending_orders(self):
        if not self.pending_orders: return
        now = datetime.now()
        active_orders = []

        for p_order in self.pending_orders:
            order_id = p_order['order_id']
            order_time = p_order['time']
            strat_tag = p_order.get('tag')
            sym = p_order.get('sym')

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

    def _update_daily_targets(self):
        now = datetime.now(self.timezone)
        current_date = now.date()
        if self.last_trading_date != current_date or not self.active_targets:
            logger.info("📅 [시스템] 새로운 거래일. 스캐너를 가동하여 타겟을 선별합니다.")
            import utils.screener as screener
            self.active_targets = screener.run_daily_screener(UNIVERSE_TICKERS, top_n=5)
            self.daily_buy_counts = {} # 전략별 독립 카운팅을 위해 빈 딕셔너리로 초기화
            self.news_danger_status = {sym: False for sym in self.active_targets}
            self.last_trading_date = current_date

    def _is_trading_time(self):
        now = datetime.now(self.timezone)
        current_time_str = now.strftime("%H:%M")
        return TRADE_START_TIME <= current_time_str <= TRADE_END_TIME

    def _execute_buy(self, sym: str, strat_tag: str, amount_usd: float, current_price: float):
        key = f"{strat_tag}_{sym}"
        buys_today = self.daily_buy_counts.get(key, 0)
        if buys_today >= MAX_DAILY_BUYS_PER_SYMBOL:
            return

        now = datetime.now(self.timezone)
        
        # 1. 쿨다운 검사 (연속 매수 방지)
        last_time = self.last_buy_time.get(key)
        if last_time:
            from config import COOLDOWN_MINUTES
            elapsed_mins = (now - last_time).total_seconds() / 60.0
            if elapsed_mins < COOLDOWN_MINUTES:
                return
                
        # 2. 추가 매수(물타기) 시 가격 간격 검사
        import utils.mock_account as mock
        data = mock.get_virtual_balance() if self.broker.is_simulation_mode else None
        
        qty = 0.0
        avg_price = 0.0
        if data:
            pos_info = data["positions"].get(strat_tag, {}).get(sym)
            if pos_info:
                qty = pos_info.get("qty", 0.0)
                avg_price = pos_info.get("avg_price", 0.0)
        else:
            qty = self.positions[strat_tag].get(sym, 0.0)
            # 실제 DB가 없는 버전에서는 방어적으로 임의 통과 취급
            avg_price = current_price if qty <= 0 else 99999
            
        if qty > 0 and avg_price > 0:
            from config import DCA_PRICE_DROP_PCT
            target_drop_price = avg_price * (1 - DCA_PRICE_DROP_PCT)
            if current_price > target_drop_price:
                # 평단가에서 최소 -2% 하락하지 않았으면 추가 매입 진입 보류
                return

        quantity = round(amount_usd / current_price, 2)
        if quantity <= 0: return

        order_seq = buys_today + 1
        logger.info(f"🚀 [{strat_tag}] {sym} 타점 도달! ({order_seq}회차 진입) {quantity}주 매수 진입 시도.")
        self.daily_buy_counts[key] = order_seq
        
        ord_res = self.broker.place_buy_order(sym, quantity, strategy_tag=strat_tag)
        
        if ord_res:
            order_id = ord_res.get('order_id')
            if ord_res.get('status') == "filled":
                exec_price = ord_res.get('executed_price')
                logger.info(f"✅ [{strat_tag}] 즉시 체결! 평균가: {exec_price}")
                
                self.last_buy_time[key] = now
                # 텔레그램 매수 알림
                round_txt = f"{order_seq}회차 추가 물타기" if order_seq > 1 else "1회차 신규 진입"
                msg = f"🤖 <b>[매수 체결 완료] ({round_txt})</b>\n\n📌 전략: <b>{strat_tag}</b>\n티커: {sym}\n수량: {quantity:g}주\n단가: ${exec_price:.2f}"
                telebot.send_telegram_message(msg)
                
                val = self.positions[strat_tag].get(sym, 0.0)
                self.positions[strat_tag][sym] = val + quantity
            else:
                logger.warning(f"⏳ [{strat_tag}] 미체결 대기열 진입. (ID: {order_id})")
                self.pending_orders.append({"order_id": order_id, "time": datetime.now(), "tag": strat_tag, "sym": sym})
        else:
            logger.error(f"❌ [{strat_tag}] 매수 주문 전송 자체 실패.")
            self.daily_buy_counts[sym] -= 1

    def evaluate_strategy_A(self, sym, df, current_price, cash):
        if cash < TRADE_AMOUNT_STRAT_A: return
        target_price = ind.calculate_breakout_target(df, 0.5)
        if target_price and current_price >= target_price:
            self._execute_buy(sym, "STRAT_A", TRADE_AMOUNT_STRAT_A, current_price)

    def evaluate_strategy_B(self, sym, df, current_price, cash):
        if cash < TRADE_AMOUNT_STRAT_B: return
        target_price = ind.calculate_breakout_target(df, 0.5)
        is_breakout = target_price and current_price >= target_price
        is_uptrend = ind.calculate_ma_condition(df, 20)
        is_vol_spike = ind.check_volume_spike(df, REQUIRE_VOLUME_SPIKE_MULTI)
        if is_breakout and is_uptrend and is_vol_spike:
            self._execute_buy(sym, "STRAT_B", TRADE_AMOUNT_STRAT_B, current_price)

    def evaluate_strategy_C(self, sym, df, bm_df, current_price, cash):
        if cash < TRADE_AMOUNT_STRAT_C: return
        if not ind.is_macro_trend_bullish(bm_df, 200): return
        if ind.check_bollinger_rsi_condition(df):
            self._execute_buy(sym, "STRAT_C", TRADE_AMOUNT_STRAT_C, current_price)

    def process_timecuts(self):
        now = datetime.now(self.timezone)
        if now.hour == TIMECUT_HOUR and now.minute >= TIMECUT_MINUTE:
            if self.broker.is_simulation_mode:
                import utils.mock_account as mock
                data = mock.get_virtual_balance()
                strat_a_holdings = data["positions"].get("STRAT_A", {})
                for sym, info in strat_a_holdings.items():
                    qty = info.get("qty", 0)
                    if qty > 0:
                        logger.critical(f"⏰ [Timecut] STRAT_A 오버나잇 금지 강제 청산: {sym} {qty}주")
                        res = self.broker.place_sell_order(sym, qty, strategy_tag="STRAT_A")
                        if res and res.get('status') == "filled":
                            msg = f"⏰ <b>[강제 타임컷 매도]</b>\n\n📌 전략: <b>STRAT_A</b>\n티커: {sym}\n수량: {qty:g}주 팔고 퇴근합니다!"
                            telebot.send_telegram_message(msg)
            else:
                for sym, qty in list(self.positions["STRAT_A"].items()):
                    if qty > 0:
                        res = self.broker.place_sell_order(sym, qty, strategy_tag="STRAT_A")
                        if res and res.get('status') == "filled":
                            msg = f"⏰ <b>[강제 타임컷 매도]</b>\n\n📌 전략: STRAT_A\n티커: {sym}\n수량: {qty:g}주 매도 처리 완료!"
                            telebot.send_telegram_message(msg)
                        self.positions["STRAT_A"][sym] = 0

    def check_exit_conditions(self, current_prices_dict):
        """실시간 수익률을 검사하여 각 전략에 부여된 익절(TP)/손절(SL) 조건에 닿으면 즉시 시장가 청산을 집행합니다."""
        if not self.broker.is_simulation_mode:
            return 
            
        import utils.mock_account as mock
        data = mock.get_virtual_balance()
        
        limits = {
            "STRAT_A": (STRAT_A_TP, STRAT_A_SL),
            "STRAT_B": (STRAT_B_TP, STRAT_B_SL),
            "STRAT_C": (STRAT_C_TP, STRAT_C_SL)
        }
        
        for strat, symbols_dict in data["positions"].items():
            if strat not in limits: continue
            tp_limit, sl_limit = limits[strat]
            
            for sym, info in list(symbols_dict.items()):
                qty = info.get("qty", 0.0)
                avg = info.get("avg_price", 0.0)
                cur_p = current_prices_dict.get(sym)
                
                if qty <= 0 or not avg or not cur_p: continue
                pnl_pct = (cur_p - avg) / avg
                
                if pnl_pct >= tp_limit:
                    logger.critical(f"🎉 [{strat}] 자동 익절선(+{tp_limit*100}%) 도달! {sym} 수익률: +{pnl_pct*100:.2f}%")
                    res = self.broker.place_sell_order(sym, qty, strategy_tag=strat)
                    if res and res.get("status") == "filled":
                        msg = f"🎉 <b>[목표 수익 도달 익절]</b>\n\n📌 전략: <b>{strat}</b>\n티커: {sym}\n수량: {qty:g}주 팔고 차익 실현!"
                        telebot.send_telegram_message(msg)
                        
                elif pnl_pct <= sl_limit:
                    logger.critical(f"🩸 [{strat}] 자동 손절선({sl_limit*100}%) 이탈! {sym} 수익률: {pnl_pct*100:.2f}%")
                    res = self.broker.place_sell_order(sym, qty, strategy_tag=strat)
                    if res and res.get("status") == "filled":
                        msg = f"🩸 <b>[리스크 손절 집행]</b>\n\n📌 전략: <b>{strat}</b>\n티커: {sym}\n수량: {qty:g}주 방어 매도 완료!"
                        telebot.send_telegram_message(msg)

    def execute_strategy(self):
        self._update_daily_targets()
        
        if not self.active_targets:
            logger.error("🚫 스캔된 타겟이 없어 오늘 매매를 멈춥니다.")
            return

        # 1. 모든 타겟 종목의 현재가 조회
        current_prices_dict = {}
        for sym in self.active_targets:
            price_info = self.broker.get_current_price(sym)
            if price_info:
                current_prices_dict[sym] = price_info.get("price")
        
        # 2. 대시보드 렌더링 및 청산 검사
        self.render_dashboard(current_prices_dict)
        self.check_exit_conditions(current_prices_dict)
        
        self._check_pending_orders()
        self.process_timecuts() 

        if not self._is_trading_time():
            return

        acc = self.broker.get_account_balance()
        if not acc: return
        cash = acc.get("cash", 0)

        bm_df = md.fetch_benchmark_data(SP500_SYMBOL, period="250d")
        
        # 3. 타겟별 매수 타점 분석
        for sym in self.active_targets:
            # 뉴스 통제 중이면 해당 종목 신규 진입 패스
            if self.news_danger_status.get(sym, False):
                continue
                
            cur_price = current_prices_dict.get(sym)
            if not cur_price: continue
            
            df = md.fetch_historical_data(sym, period="60d")
            if df is None or len(df) < 22: continue
            
            self.evaluate_strategy_A(sym, df, cur_price, cash)
            self.evaluate_strategy_B(sym, df, cur_price, cash)
            if bm_df is not None:
                self.evaluate_strategy_C(sym, df, bm_df, cur_price, cash)
