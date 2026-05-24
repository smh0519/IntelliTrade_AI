# config.py

# --- 거래 유니버스: 나스닥 100 시가총액 상위 50 ---
UNIVERSE_TICKERS = [
    # 메가캡 (1-10)
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX",
    # 대형 기술주 (11-20)
    "ASML", "AMD", "QCOM", "ISRG", "CSCO", "TXN", "PEP", "ADBE", "AMAT", "INTU",
    # 대형 기술주 (21-30)
    "MU", "REGN", "LRCX", "KLAC", "MRVL", "PANW", "CRWD", "ADI", "AMGN", "ARM",
    # 중대형주 (31-40)
    "SNPS", "CDNS", "FTNT", "MELI", "CTAS", "ORLY", "ABNB", "MNST", "PAYX", "ROST",
    # 중형주 (41-50)
    "CPRT", "ON", "TEAM", "GEHC", "TTD", "VRSK", "IDXX", "DXCM", "WDAY", "ZS",
]

# --- N10-MEW 전략 파라미터 ---
MOMENTUM_PERIOD_DAYS = 63        # 3개월 모멘텀 계산 기간 (약 63 영업일)
TOP_N_PORTFOLIO = 10             # 포트폴리오 편입 종목 수
REBALANCE_EXIT_RANK = 12         # 이 순위 밖으로 밀리면 즉시 교체
WEIGHT_PER_STOCK = 0.10          # 종목당 동일 비중 (10%)
REBALANCE_THRESHOLD = 0.02       # 비중 오차가 2% 이상일 때만 조정 (거래비용 절감)
REBALANCE_EXECUTION_TIME = "09:30"  # 리밸런싱 집행 시각 (뉴욕 기준, 정규장 개장 즉시)

# --- 리스크 관리 ---
PORTFOLIO_STOP_LOSS = -0.20      # 전체 포트폴리오 -20% 이탈 시 경고 알림
MIN_CASH_BALANCE = 500           # 리밸런싱 후 유지할 최소 현금 잔고 ($)
SLIPPAGE_TOLERANCE = 0.005       # 허용 슬리피지 (0.5%)

# --- 주문 설정 ---
ORDER_TIMEOUT_MINUTES = 5        # 미체결 주문 타임아웃 (분)
UNFILLED_ORDER_ACTION = "cancel" # 타임아웃 시 조치: cancel

# --- 벤치마크 ---
BENCHMARK_SYMBOL = "QQQ"         # 성과 비교 벤치마크 (나스닥 100 ETF)

# --- 시간 설정 ---
TRADE_START_TIME = "09:30"       # 정규장 시작 (뉴욕 기준)
TRADE_END_TIME = "16:00"         # 정규장 종료 (뉴욕 기준)
TIMEZONE = "America/New_York"

# --- 로깅 ---
LOG_LEVEL = "INFO"
LOG_FILE_PATH = "trading_bot.log"
