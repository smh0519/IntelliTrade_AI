import os
import requests
import json
import time
from functools import wraps
from dotenv import load_dotenv
from utils.logger import logger

def handle_broker_errors(max_retries=3, initial_delay=1.0, backoff_factor=2):
    """API 호출 시 발생할 수 있는 429 에러나 타임아웃을 강어하는 백오프 데코레이터입니다."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429 or (500 <= e.response.status_code < 600):
                        logger.warning(f"통신 지연({e.response.status_code}). {delay}초 대기 후 재시도... ({retries+1}/{max_retries})")
                        time.sleep(delay)
                        delay *= backoff_factor
                        retries += 1
                    else:
                        raise # 400 등 인증 거절 에러는 즉시 발생
                except requests.exceptions.RequestException as e:
                    logger.error(f"통신 에러 발생: {e}. {delay}초 뒤 재시도...")
                    time.sleep(delay)
                    delay *= backoff_factor
                    retries += 1
            logger.error(f"주문 통신 {max_retries}회 재시도 최종 실패.")
            return None
        return wrapper
    return decorator

# .env 파일 로드
load_dotenv()

class BrokerAPIClient:
    """
    증권사 API와 통신하는 클라이언트 클래스입니다.
    실제 증권사 API 명세에 맞춰 구현해야 합니다.
    """
    def __init__(self):
        self.api_key = os.getenv("BROKER_API_KEY")
        self.secret_key = os.getenv("BROKER_SECRET_KEY")
        self.account_id = os.getenv("BROKER_ACCOUNT_ID")
        self.base_url = os.getenv("BROKER_API_BASE_URL", "https://api.examplebroker.com") # 기본 URL 설정
        self.is_simulation_mode = os.getenv("IS_SIMULATION_MODE", "True").lower() == "true"

        if not self.is_simulation_mode and not all([self.api_key, self.secret_key, self.account_id]):
            logger.error("API 키, 시크릿 키, 계좌 ID가 .env 파일에 설정되지 않았습니다.")
            raise ValueError("API credentials not set.")

        logger.info(f"BrokerAPIClient 초기화 완료. 시뮬레이션 모드: {self.is_simulation_mode}")

    def _get_headers(self):
        """
        API 요청에 필요한 헤더를 생성합니다.
        (각 증권사 API 명세에 따라 인증 방식이 다를 수 있습니다.)
        """
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
            "X-API-SECRET": self.secret_key,
            # 추가적인 인증 토큰 등이 필요할 수 있습니다.
        }
        return headers

    @handle_broker_errors()
    def get_account_balance(self):
        """
        계좌 잔고를 조회합니다.
        (실제 증권사 API 엔드포인트와 응답 형식에 맞춰 구현해야 합니다.)
        """
        if self.is_simulation_mode:
            import utils.mock_account as mock
            data = mock.get_virtual_balance()
            logger.info(f"시뮬레이션 모드: 가상 계좌 잔고를 반환합니다. ({data['cash']} {data['currency']})")
            return data
        
        url = f"{self.base_url}/v1/accounts/{self.account_id}/balance"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status() # HTTP 에러 발생 시 예외 발생
            data = response.json()
            logger.info(f"계좌 잔고 조회 성공: {data}")
            # 실제 응답에서 현금 잔고를 파싱하여 반환
            return {"cash": data.get("available_cash"), "currency": data.get("currency")}
        except requests.exceptions.RequestException as e:
            logger.error(f"계좌 잔고 조회 실패: {e}")
            return None
        except KeyError as e:
            logger.error(f"계좌 잔고 응답 파싱 실패 (키 오류): {e}, 응답: {response.text}")
            return None

    @handle_broker_errors()
    def get_current_price(self, symbol: str):
        """
        특정 종목의 현재 가격을 조회합니다.
        (실제 증권사 API 엔드포인트와 응답 형식에 맞춰 구현해야 합니다.)
        """
        if self.is_simulation_mode:
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                # fast_info를 통해 현재 가장 최신의 미국장 시세를 가져옵니다.
                price = ticker.fast_info['lastPrice']
                logger.info(f"시뮬레이션 모드 (Live): {symbol}의 실시간 현재가 -> {price:.2f} USD")
                return {"price": round(price, 2), "currency": "USD"}
            except Exception as e:
                logger.error(f"시뮬레이션 라이브 시세 조회 실패: {e}")
                return None
            
        url = f"{self.base_url}/v1/market/quotes/{symbol}"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()
            logger.debug(f"{symbol} 현재가 조회 성공: {data}")
            return {"price": data.get("current_price"), "currency": data.get("currency")}
        except requests.exceptions.RequestException as e:
            logger.error(f"{symbol} 현재가 조회 실패: {e}")
            return None

    @handle_broker_errors()
    def place_buy_order(self, symbol: str, quantity: float, price: float = None, strategy_tag: str = "MANUAL"):
        """
        매수 주문을 실행합니다.
        (실제 증권사 API 엔드포인트와 요청/응답 형식에 맞춰 구현해야 합니다.)
        price가 None이면 시장가 주문, price가 있으면 지정가 주문으로 가정합니다.
        """
        order_type = "market" if price is None else "limit"
        order_data = {
            "symbol": symbol,
            "side": "buy",
            "quantity": quantity,
            "order_type": order_type,
            "price": price, # 지정가 주문일 경우에만 포함
            "account_id": self.account_id,
            "strategy_tag": strategy_tag
        }
        
        if self.is_simulation_mode:
            logger.info(f"시뮬레이션 모드: 📝 매수 주문 실행 중... (종목: {symbol}, 수량: {quantity}, 전략: {strategy_tag})")
            import utils.mock_account as mock
            
            # 지정가가 없으면 실시간 현재가로 매수
            exec_price = price if price else self.get_current_price(symbol)['price']
            res_price = mock.execute_virtual_buy(symbol, quantity, exec_price, strategy_tag)
            
            if res_price is None:
                return None
            return {"order_id": f"SIM_BUY_{int(time.time())}", "status": "filled", "executed_price": res_price}

        url = f"{self.base_url}/v1/orders"
        try:
            response = requests.post(url, headers=self._get_headers(), json=order_data)
            response.raise_for_status()
            data = response.json()
            logger.info(f"매수 주문 성공: {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"매수 주문 실패: {e}, 요청 데이터: {order_data}, 응답: {response.text}")
            return None

    @handle_broker_errors()
    def place_sell_order(self, symbol: str, quantity: float, price: float = None, strategy_tag: str = "MANUAL"):
        """
        매도 주문을 실행합니다.
        """
        order_type = "market" if price is None else "limit"
        order_data = {
            "symbol": symbol,
            "side": "sell",
            "quantity": quantity,
            "order_type": order_type,
            "price": price,
            "account_id": self.account_id,
            "strategy_tag": strategy_tag
        }

        if self.is_simulation_mode:
            logger.info(f"시뮬레이션 모드: 📝 매도 주문 실행 중... (종목: {symbol}, 수량: {quantity}, 전략: {strategy_tag})")
            import utils.mock_account as mock
            
            exec_price = price if price else self.get_current_price(symbol)['price']
            res_price = mock.execute_virtual_sell(symbol, quantity, exec_price, strategy_tag)
            
            if res_price is None:
                return None
            return {"order_id": f"SIM_SELL_{int(time.time())}", "status": "filled", "executed_price": res_price}

        url = f"{self.base_url}/v1/orders"
        try:
            response = requests.post(url, headers=self._get_headers(), json=order_data)
            response.raise_for_status()
            data = response.json()
            logger.info(f"매도 주문 성공: {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"매도 주문 실패: {e}, 요청 데이터: {order_data}, 응답: {response.text}")
            raise # 데코레이터에서 잡히도록 throw

    @handle_broker_errors()
    def get_order_status(self, order_id: str):
        """특정 주문의 체결 상태(filled, partial, pending, canceled, rejected)를 반환합니다."""
        if self.is_simulation_mode:
            logger.debug(f"시뮬레이션 모드: 체결 상태 확인 (ID: {order_id})")
            # 시뮬레이션에서는 대충 성공으로 치기보다는 랜덤 딜레이 구현이 좋으나,
            # 확인 편의상 대기는 안하고 바로 'filled'로 넘깁니다. (실제 테스트시엔 수정)
            return {"order_id": order_id, "status": "filled", "timestamp": time.time()}

        url = f"{self.base_url}/v1/orders/{order_id}"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    @handle_broker_errors()
    def cancel_order(self, order_id: str):
        """미체결 상태이거나 부분 체결된 주문을 취소합니다."""
        if self.is_simulation_mode:
            logger.info(f"시뮬레이션 모드: 미체결 주문 취소 성공 (ID: {order_id})")
            return {"order_id": order_id, "status": "canceled"}

        url = f"{self.base_url}/v1/orders/{order_id}/cancel"
        response = requests.post(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        logger.info(f"주문 ID {order_id} 강제 취소 성공: {data}")
        return data
