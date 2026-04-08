# config.py

# --- 거래 설정 ---
TARGET_STOCK_SYMBOL = "AAPL"  # 거래할 종목 심볼 (예: 삼성전자 '005930', Apple 'AAPL')
# 총 투자금 300달러를 각 전략에 독립적으로 분배
TRADE_AMOUNT_STRAT_A = 100    # 전략 A (래리 윌리엄스 돌파 + 타임컷) 예산
TRADE_AMOUNT_STRAT_B = 100    # 전략 B (하이브리드 추세 돌파) 예산
TRADE_AMOUNT_STRAT_C = 100    # 전략 C (볼린저 + RSI 과매도 스윙) 예산
MIN_CASH_BALANCE = 500        # 최소 현금 잔고 (이 금액 이하이면 매수하지 않음)
MAX_DAILY_BUYS_PER_SYMBOL = 3 # 종목별 하루 최대 허용 매수 횟수
SLIPPAGE_TOLERANCE = 0.005    # 허용 가능한 슬리피지 (0.5%)
ORDER_TIMEOUT_MINUTES = 3     # 주문 미체결 시 타임아웃 간격(분)
UNFILLED_ORDER_ACTION = "cancel" # 미체결 타임아웃 도달 시 조치 방식 (cancel 등)

# --- 전략 필터 파라미터 ---
REQUIRE_VOLUME_SPIKE_MULTI = 2.0 # 전략 B 필터: 어제 거래량이 20일 평균의 몇 배 이상 터져야 하는지
TIMECUT_HOUR = 15             # 전략 A 타임컷: 강제 매도 및 포지션 청산 시간 (시간)
TIMECUT_MINUTE = 15           # 전략 A 타임컷: (분)
SP500_SYMBOL = "SPY"          # 전략 C 필터: 대세 하락장을 판별할 기준 마켓 ETF (S&P 500)

# --- 시간 설정 ---
TRADE_START_TIME = "09:00"    # 거래 시작 시간 (KST)
TRADE_END_TIME = "15:20"      # 거래 종료 시간 (KST)
TIMEZONE = "Asia/Seoul"       # 시간대 설정

# --- 로깅 설정 ---
LOG_LEVEL = "INFO"            # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE_PATH = "trading_bot.log" # 로그 파일 경로

# --- 기타 설정 ---
# IS_SIMULATION_MODE는 .env에서 로드되므로 여기에 직접 정의하지 않습니다.
# 하지만, .env에서 로드된 값을 참조하여 추가적인 설정을 할 수 있습니다.

# 예시: 특정 증권사 API의 추가 설정 (필요시)
# KOREA_EXCHANGE_CODE = "KRX"
