import os
import requests
import time
from functools import wraps
from dotenv import load_dotenv
from utils.logger import logger

load_dotenv()


def handle_broker_errors(max_retries=3, initial_delay=1.0, backoff_factor=2):
    """429·5xx 에러 시 지수 백오프로 재시도하는 데코레이터."""
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
                        raise
                except requests.exceptions.RequestException as e:
                    logger.error(f"통신 에러 발생: {e}. {delay}초 뒤 재시도...")
                    time.sleep(delay)
                    delay *= backoff_factor
                    retries += 1
            logger.error(f"주문 통신 {max_retries}회 재시도 최종 실패.")
            return None
        return wrapper
    return decorator


# ── 미래에셋 Open API 기본 URL ────────────────────────────────────────
MIRAEASSET_BASE_URL = "https://openapi.miraeasset.com"  # 실제 URL은 API 승인 후 확인


class BrokerAPIClient:
    """
    증권사 API 클라이언트.

    시작 순서:
      1. Supabase user_broker_credentials 테이블에서 자격증명 로드 (user_id 필요)
      2. 없으면 .env 폴백 (BROKER_API_KEY, BROKER_SECRET_KEY 등)
      3. is_simulation_mode=True면 yfinance + 가상계좌로 동작
    """

    def __init__(self, user_id: str = ""):
        creds = self._load_supabase_credentials(user_id) if user_id else None

        if creds:
            logger.info("[BrokerAPI] Supabase에서 자격증명 로드 완료")
            self.api_key          = creds.get("api_key") or ""
            self.secret_key       = creds.get("secret_key") or ""
            self.account_id       = creds.get("account_id") or ""
            self.base_url         = creds.get("base_url") or MIRAEASSET_BASE_URL
            self.is_simulation_mode = creds.get("is_simulation_mode", True)
        else:
            logger.info("[BrokerAPI] .env에서 자격증명 로드")
            self.api_key          = os.getenv("BROKER_API_KEY", "")
            self.secret_key       = os.getenv("BROKER_SECRET_KEY", "")
            self.account_id       = os.getenv("BROKER_ACCOUNT_ID", "")
            self.base_url         = os.getenv("BROKER_API_BASE_URL", MIRAEASSET_BASE_URL)
            self.is_simulation_mode = os.getenv("IS_SIMULATION_MODE", "True").lower() == "true"

        if not self.is_simulation_mode and not all([self.api_key, self.secret_key, self.account_id]):
            logger.error("실계좌 모드인데 API 키/시크릿/계좌번호가 비어 있습니다.")
            raise ValueError("브로커 자격증명이 설정되지 않았습니다.")

        self._access_token: str = ""
        self._token_expires_at: float = 0.0

        logger.info(f"BrokerAPIClient 초기화 완료. 시뮬레이션 모드: {self.is_simulation_mode}")

    # ── 내부 유틸 ────────────────────────────────────────────────────

    @staticmethod
    def _load_supabase_credentials(user_id: str) -> dict | None:
        try:
            from utils.supabase_client import load_broker_credentials
            return load_broker_credentials(user_id)
        except Exception as e:
            logger.warning(f"[BrokerAPI] Supabase 자격증명 로드 실패 → .env 폴백: {e}")
            return None

    def _get_access_token(self) -> str:
        """
        미래에셋 OAuth 액세스 토큰을 발급·갱신합니다.

        ※ 실제 엔드포인트·파라미터는 미래에셋 Open API 문서 확인 후 채워주세요.
        """
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        url = f"{self.base_url}/oauth/token"  # TODO: 미래에셋 실제 토큰 발급 URL
        payload = {
            "grant_type":    "client_credentials",
            "appkey":        self.api_key,
            "appsecretkey":  self.secret_key,
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            res.raise_for_status()
            data = res.json()
            self._access_token    = data["access_token"]          # TODO: 응답 키 확인
            expires_in            = data.get("expires_in", 3600)  # TODO: 응답 키 확인
            self._token_expires_at = time.time() + expires_in
            logger.info("[BrokerAPI] 미래에셋 액세스 토큰 발급 완료")
        except Exception as e:
            logger.error(f"[BrokerAPI] 토큰 발급 실패: {e}")
        return self._access_token

    def _get_headers(self) -> dict:
        return {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {self._get_access_token()}",
            "appkey":        self.api_key,       # TODO: 미래에셋 헤더 명세 확인
            "appsecretkey":  self.secret_key,
        }

    # ── 계좌 잔고 ────────────────────────────────────────────────────

    @handle_broker_errors()
    def get_account_balance(self) -> dict | None:
        if self.is_simulation_mode:
            import utils.mock_account as mock
            data = mock.get_virtual_balance()
            logger.info(f"[시뮬] 가상계좌 잔고: ${data['cash']:.2f}")
            return data

        # TODO: 미래에셋 잔고 조회 엔드포인트·응답 파싱 채우기
        url = f"{self.base_url}/v1/accounts/{self.account_id}/balance"
        try:
            res = requests.get(url, headers=self._get_headers(), timeout=10)
            res.raise_for_status()
            data = res.json()
            return {"cash": data.get("available_cash"), "currency": "USD"}
        except requests.exceptions.RequestException as e:
            logger.error(f"[BrokerAPI] 잔고 조회 실패: {e}")
            return None

    # ── 현재가 ───────────────────────────────────────────────────────

    @handle_broker_errors()
    def get_current_price(self, symbol: str) -> dict | None:
        if self.is_simulation_mode:
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d", interval="1m", prepost=True)
                price = float(hist["Close"].iloc[-1]) if not hist.empty else ticker.fast_info["lastPrice"]
                logger.info(f"[시뮬] {symbol} 실시간 현재가: ${price:.2f}")
                return {"price": round(price, 2), "currency": "USD"}
            except Exception as e:
                logger.error(f"[시뮬] {symbol} 시세 조회 실패: {e}")
                return None

        # TODO: 미래에셋 시세 조회 엔드포인트·응답 파싱 채우기
        url = f"{self.base_url}/v1/market/quotes/{symbol}"
        try:
            res = requests.get(url, headers=self._get_headers(), timeout=10)
            res.raise_for_status()
            data = res.json()
            return {"price": data.get("current_price"), "currency": "USD"}
        except requests.exceptions.RequestException as e:
            logger.error(f"[BrokerAPI] {symbol} 현재가 조회 실패: {e}")
            return None

    # ── 매수 주문 ────────────────────────────────────────────────────

    @handle_broker_errors()
    def place_buy_order(self, symbol: str, quantity: float, price: float = None, strategy_tag: str = "MANUAL") -> dict | None:
        if self.is_simulation_mode:
            import utils.mock_account as mock
            exec_price = price if price else self.get_current_price(symbol)["price"]
            res_price = mock.execute_virtual_buy(symbol, quantity, exec_price, strategy_tag)
            if res_price is None:
                return None
            logger.info(f"[시뮬] 매수 체결: {symbol} {quantity}주 @ ${res_price:.2f}")
            return {"order_id": f"SIM_BUY_{int(time.time())}", "status": "filled", "executed_price": res_price}

        # TODO: 미래에셋 매수 주문 엔드포인트·응답 파싱 채우기
        order_data = {
            "symbol":       symbol,
            "side":         "buy",
            "quantity":     quantity,
            "order_type":   "market" if price is None else "limit",
            "price":        price,
            "account_id":   self.account_id,
        }
        url = f"{self.base_url}/v1/orders"
        try:
            res = requests.post(url, headers=self._get_headers(), json=order_data, timeout=10)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[BrokerAPI] 매수 주문 실패: {e}")
            return None

    # ── 매도 주문 ────────────────────────────────────────────────────

    @handle_broker_errors()
    def place_sell_order(self, symbol: str, quantity: float, price: float = None, strategy_tag: str = "MANUAL") -> dict | None:
        if self.is_simulation_mode:
            import utils.mock_account as mock
            exec_price = price if price else self.get_current_price(symbol)["price"]
            res_price = mock.execute_virtual_sell(symbol, quantity, exec_price, strategy_tag)
            if res_price is None:
                return None
            logger.info(f"[시뮬] 매도 체결: {symbol} {quantity}주 @ ${res_price:.2f}")
            return {"order_id": f"SIM_SELL_{int(time.time())}", "status": "filled", "executed_price": res_price}

        # TODO: 미래에셋 매도 주문 엔드포인트·응답 파싱 채우기
        order_data = {
            "symbol":       symbol,
            "side":         "sell",
            "quantity":     quantity,
            "order_type":   "market" if price is None else "limit",
            "price":        price,
            "account_id":   self.account_id,
        }
        url = f"{self.base_url}/v1/orders"
        try:
            res = requests.post(url, headers=self._get_headers(), json=order_data, timeout=10)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[BrokerAPI] 매도 주문 실패: {e}")
            raise

    # ── 주문 상태 / 취소 ─────────────────────────────────────────────

    @handle_broker_errors()
    def get_order_status(self, order_id: str) -> dict | None:
        if self.is_simulation_mode:
            return {"order_id": order_id, "status": "filled", "timestamp": time.time()}

        # TODO: 미래에셋 주문 상태 조회 엔드포인트 채우기
        url = f"{self.base_url}/v1/orders/{order_id}"
        res = requests.get(url, headers=self._get_headers(), timeout=10)
        res.raise_for_status()
        return res.json()

    @handle_broker_errors()
    def cancel_order(self, order_id: str) -> dict | None:
        if self.is_simulation_mode:
            logger.info(f"[시뮬] 주문 취소: {order_id}")
            return {"order_id": order_id, "status": "canceled"}

        # TODO: 미래에셋 주문 취소 엔드포인트 채우기
        url = f"{self.base_url}/v1/orders/{order_id}/cancel"
        res = requests.post(url, headers=self._get_headers(), timeout=10)
        res.raise_for_status()
        return res.json()
