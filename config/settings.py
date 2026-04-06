import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- API Keys ---
# 실제 사용 시에는 .env 파일에 저장하고 os.getenv()로 불러오는 것을 강력히 권장합니다.
# 예: GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # Gemini API 키 (gemini_pro.py에서 사용)

# --- Trading API Keys (예시: 증권사 API) ---
# 실제 증권사 API 키와 시크릿은 여기에 직접 노출하지 말고 .env 파일에서 불러오세요.
# TRADING_API_KEY = os.getenv("TRADING_API_KEY")
# TRADING_SECRET = os.getenv("TRADING_SECRET")
# TRADING_ACCOUNT_ID = os.getenv("TRADING_ACCOUNT_ID")

# --- General Settings ---
APP_NAME = "QuantStockTrader"
VERSION = "1.0.0"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper() # 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

# --- Trading Strategy Settings ---
# 예시 값이며, 실제 전략에 따라 변경됩니다.
DEFAULT_CASH_ALLOCATION_PERCENT = 0.10 # 한 종목당 할당할 현금 비율 (10%)
MIN_TRADING_VOLUME = 1000000000 # 최소 거래량 (10억) 이상 종목만 고려
RISK_FREE_RATE = 0.02 # 무위험 이자율 (연 2%)
LOOKBACK_PERIOD_DAYS = 252 # 전략 분석을 위한 과거 데이터 기간 (1년 영업일)

# --- Data Settings ---
DATA_SOURCE = "KRX" # 데이터 출처 (예: KRX, Yahoo Finance 등)
STOCK_LIST_UPDATE_INTERVAL_DAYS = 7 # 종목 목록 업데이트 주기

# --- Database Settings (필요 시) ---
# DB_URI = os.getenv("DATABASE_URL", "sqlite:///quant_data.db")

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # config 폴더의 상위 디렉토리
LOG_FILE_PATH = os.path.join(BASE_DIR, 'logs', 'app.log') # 로그 파일 경로

# 로깅 설정 디렉토리 생성 확인
LOG_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# --- 웹소켓 관련 설정 (실시간 데이터 필요 시) ---
# WEBSOCKET_URL = "ws://your_broker_websocket_url"
# WEBSOCKET_RECONNECT_INTERVAL_SECONDS = 5

# --- 백테스팅 설정 (추후 구현 시) ---
# BACKTEST_START_DATE = "2020-01-01"
# BACKTEST_END_DATE = "2023-12-31"
# INITIAL_BACKTEST_CAPITAL = 100_000_000 # 1억원

# --- 알림 설정 (슬랙, 텔레그램 등) ---
# SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 이외에도 필요한 설정들을 추가할 수 있습니다.
