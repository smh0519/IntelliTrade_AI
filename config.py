# config.py

# --- 거래(스캔) 대상 유니버스 ---
# 나스닥/S&P 주요 메가테크 및 초우량주 약 30종 (매일 아침 이들 중 Top 5를 선별합니다)
UNIVERSE_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "AVGO", "JPM",
    "UNH", "V", "XOM", "MA", "JNJ", "PG", "HD", "MRK", "COST", "ABBV", 
    "CRM", "AMD", "NFLX", "ADBE", "QCOM", "INTC", "CSCO", "PEP", "KO", "BAC"
]
# 총 투자금 300달러를 각 전략에 독립적으로 분배
TRADE_AMOUNT_STRAT_A = 100    # 전략 A (래리 윌리엄스 돌파 + 타임컷) 예산
TRADE_AMOUNT_STRAT_B = 100    # 전략 B (하이브리드 추세 돌파) 예산
TRADE_AMOUNT_STRAT_C = 100    # 전략 C (볼린저 + RSI 과매도 스윙) 예산
MIN_CASH_BALANCE = 500        # 최소 현금 잔고 (이 금액 이하이면 매수하지 않음)
MAX_DAILY_BUYS_PER_SYMBOL = 3 # 종목별 하루 최대 허용 매수 횟수
COOLDOWN_MINUTES = 60         # 한 번 매수한 종목 및 전략은 최소 60분 대기 (연속 매수 금지)
DCA_PRICE_DROP_PCT = 0.02     # 추가 매수는 이전 투자 평단가보다 2% 이상 하락했을 때만 허용 (스마트 물타기)
SLIPPAGE_TOLERANCE = 0.005    # 허용 가능한 슬리피지 (0.5%)
ORDER_TIMEOUT_MINUTES = 3     # 주문 미체결 시 타임아웃 간격(분)
UNFILLED_ORDER_ACTION = "cancel" # 미체결 타임아웃 도달 시 조치 방식 (cancel 등)

# --- 전략 필터 파라미터 ---
REQUIRE_VOLUME_SPIKE_MULTI = 2.0 # 전략 B 필터: 어제 거래량이 20일 평균의 몇 배 이상 터져야 하는지
TIMECUT_HOUR = 15             # 전략 A 타임컷: 뉴욕장 마감 5분 전(15시 55분) 청산
TIMECUT_MINUTE = 55           # 전략 A 타임컷: (분)
SP500_SYMBOL = "SPY"          # 전략 C 필터: 대세 하락장을 판별할 기준 마켓 ETF (S&P 500)

# --- 전략별 동적 익절/손절 (TP/SL) 한도 ---
STRAT_A_TP = 0.05    # 전략 A 익절선 (+5%)
STRAT_A_SL = -0.03   # 전략 A 손절선 (-3%)
STRAT_B_TP = 0.08    # 전략 B 익절선 (+8%)
STRAT_B_SL = -0.04   # 전략 B 손절선 (-4%)
STRAT_C_TP = 0.04    # 전략 C 익절선 (+4%)
STRAT_C_SL = -0.02   # 전략 C 손절선 (-2%)

# --- 시간 설정 ---
TRADE_START_TIME = "09:30"    # 정규장 시작 시간 (뉴욕 시간 기준)
TRADE_END_TIME = "16:00"      # 정규장 종료 시간 (뉴욕 시간 기준)
TIMEZONE = "America/New_York" # 기준 타임존 (서머타임 자동 적용)

# --- 로깅 설정 ---
LOG_LEVEL = "INFO"            # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE_PATH = "trading_bot.log" # 로그 파일 경로

# --- 기타 설정 ---
# IS_SIMULATION_MODE는 .env에서 로드되므로 여기에 직접 정의하지 않습니다.
# 하지만, .env에서 로드된 값을 참조하여 추가적인 설정을 할 수 있습니다.

# 예시: 특정 증권사 API의 추가 설정 (필요시)
# KOREA_EXCHANGE_CODE = "KRX"
