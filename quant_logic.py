import pandas as pd
from datetime import datetime
from utils.api_handler import APIHandler
from utils.notifier import Notifier
from config.settings import TARGET_PROFIT_RATE, STOP_LOSS_RATE

class QuantStrategy:
    """
    퀀트 투자 전략을 정의하고 매매 결정을 내리는 클래스.
    """
    def __init__(self, api_handler: APIHandler, notifier: Notifier):
        self.api_handler = api_handler
        self.notifier = notifier
        self.holdings = {} # 현재 보유 종목 정보 {symbol: {"quantity": int, "avg_price": float}}

    def update_holdings(self):
        """현재 보유 종목 정보를 API에서 가져와 업데이트합니다."""
        holdings_data = self.api_handler.get_holdings()
        self.holdings = {item["symbol"]: {"quantity": item["quantity"], "avg_price": item["avg_price"]} for item in holdings_data}
        self.notifier.notify_info(f"보유 종목 업데이트: {self.holdings}")

    def analyze_market(self, symbol: str) -> dict:
        """
        주어진 종목에 대한 시장 데이터를 분석하고 매매 신호를 생성합니다.
        여기서는 기본적인 기술적 분석 (예: 이동평균선)을 예시로 들지만,
        Gemini Pro 모델 (`gemini_pro.py`)을 활용하여 더 복잡한 분석을 수행할 수 있습니다.
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbol} 시장 분석 시작...")
        
        # 1. 과거 데이터 조회
        market_data_raw = self.api_handler.get_market_data(symbol, period="day", count=60)
        if not market_data_raw or not market_data_raw.get("data"):
            self.notifier.notify_info(f"{symbol} 과거 데이터 조회 실패 또는 데이터 부족.") # warning -> info로 변경
            return {"signal": "hold", "reason": "데이터 부족", "current_price": 0.0} # current_price 추가

        df = pd.DataFrame(market_data_raw["data"])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df['close'] = pd.to_numeric(df['close']) # 종가를 숫자로 변환

        # 2. 기술적 지표 계산 (예: 20일 이동평균선)
        df['MA20'] = df['close'].rolling(window=20).mean()

        # 데이터가 충분하지 않아 MA20 계산이 안 되는 경우 처리
        if len(df) < 20 or df['MA20'].isnull().iloc[-1]:
            self.notifier.notify_info(f"{symbol} 이동평균선 계산을 위한 데이터 부족.")
            return {"signal": "hold", "reason": "이동평균선 계산 데이터 부족", "current_price": df['close'].iloc[-1]}


        # 3. 매매 신호 생성 (간단한 이동평균선 전략 예시)
        # 현재 종가와 20일 이동평균선을 비교
        current_price = df['close'].iloc[-1]
        ma20 = df['MA20'].iloc[-1]
        
        signal = "hold"
        reason = "관망"

        # 골든 크로스 / 데드 크로스 판단 시 이전 봉 확인 (최소 2개 봉 필요)
        if len(df) >= 2:
            prev_close = df['close'].iloc[-2]
            prev_ma20 = df['MA20'].iloc[-2]

            if current_price > ma20 and prev_close <= prev_ma20: # 골든 크로스 발생
                signal = "buy"
                reason = f"골든 크로스 발생: 현재가 {current_price:.0f} > MA20 {ma20:.0f}"
            elif current_price < ma20 and prev_close >= prev_ma20: # 데드 크로스 발생
                signal = "sell"
                reason = f"데드 크로스 발생: 현재가 {current_price:.0f} < MA20 {ma20:.0f}"
        
        # 보유 종목에 대한 손절/익절 판단
        if symbol in self.holdings and self.holdings[symbol]["quantity"] > 0:
            avg_price = self.holdings[symbol]["avg_price"]
            if current_price < avg_price * (1 - STOP_LOSS_RATE):
                signal = "sell"
                reason = f"손절 라인 도달: 현재가 {current_price:.0f}, 매수평균가 {avg_price:.0f}"
            elif current_price > avg_price * (1 + TARGET_PROFIT_RATE):
                signal = "sell"
                reason = f"목표 수익률 달성: 현재가 {current_price:.0f}, 매수평균가 {avg_price:.0f}"
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbol} 분석 결과: 신호={signal}, 이유={reason}")
        return {"signal": signal, "reason": reason, "current_price": current_price}

    def make_decision_and_execute(self, symbol: str):
        """
        분석 결과를 바탕으로 매매 결정을 내리고 주문을 실행합니다.
        """
        analysis_result = self.analyze_market(symbol)
        signal = analysis_result["signal"]
        current_price = analysis_result["current_price"]
        reason = analysis_result["reason"]

        if current_price == 0.0: # 데이터 부족 등으로 현재 가격을 알 수 없는 경우
            self.notifier.notify_warning(f"{symbol}: 현재 가격 정보를 가져올 수 없어 매매 결정을 할 수 없습니다.")
            return

        if signal == "buy":
            if symbol not in self.holdings or self.holdings[symbol]["quantity"] == 0: # 아직 보유하고 있지 않다면 매수
                # TODO: 매수 수량 결정 로직 (예: 총 자산의 N% 또는 고정 수량)
                # 시뮬레이션 모드에서는 간단하게 1주 매수
                quantity_to_buy = 1 
                order_result = self.api_handler.send_buy_order(symbol, current_price, quantity_to_buy)
                self.notifier.notify_order_status({**order_result, "symbol": symbol, "type": "buy", "price": current_price, "quantity": quantity_to_buy})
                if order_result.get("status") == "success":
                    self.update_holdings() # 매수 성공 시 보유 종목 업데이트
            else:
                self.notifier.notify_info(f"{symbol}: 이미 보유 중이므로 매수하지 않습니다. ({reason})")

        elif signal == "sell":
            if symbol in self.holdings and self.holdings[symbol]["quantity"] > 0: # 보유하고 있다면 매도
                quantity_to_sell = self.holdings[symbol]["quantity"] # 전량 매도
                order_result = self.api_handler.send_sell_order(symbol, current_price, quantity_to_sell)
                self.notifier.notify_order_status({**order_result, "symbol": symbol, "type": "sell", "price": current_price, "quantity": quantity_to_sell})
                if order_result.get("status") == "success":
                    self.update_holdings() # 매도 성공 시 보유 종목 업데이트
            else:
                self.notifier.notify_info(f"{symbol}: 보유하고 있지 않으므로 매도하지 않습니다. ({reason})")
        else:
            self.notifier.notify_info(f"{symbol}: 현재 매매 신호 없음. ({reason})")
