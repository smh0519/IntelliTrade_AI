# 📈 Advanced Quant Trading Bot

이 프로젝트는 Python 기반의 자동 매매 시스템으로, 하이브리드 멀티 전략(Multi-Strategy) 병렬 처리와 강력한 자산 방어 가이드라인(Risk Management)을 핵심으로 설계된 봇입니다. 

---

## 🛡 핵심 방어 가이드라인 (Defense Mechanisms)

실전 매매에서 알고리즘 오작동이나 휩쏘(Whipsaw), 통신 오류로 인해 계좌가 녹아내리는 것을 막기 위한 필수 안전장치들이 탑재되어 있습니다.

1. **미체결 주문 생애주기 관리 (Unfilled Order Lifecycle)**
   *   지정가 주문 또는 호가 차이로 인해 주문이 체결되지 않고 대기(Pending) 중일 경우 자산 동결을 막습니다. 
   *   **타임아웃(3분)** 초과 시 해당 주문을 강제 취소(Cancel) 처리하고 다음 기회를 노립니다.
2. **일일 종목 매수 횟수 제한 (Overtrading Prevention)**
   *   차트가 박스권에서 횡보하며 발생시키는 잦은 신호(휩쏘)에 속아 수수료를 탕진하는 것을 막습니다.
   *   한 종목에 대해 하루 최대 3회까지만 매수에 진입합니다. (매일 자정에 초기화)
   *   **주의:** 자산 보호를 위해 수익 실현 및 손절 등 '매도' 로직에는 횟수 제한을 전면 해제해 두었습니다.
3. **대세 하락장 접근 금지 (Macro Filter Lock-on)**
   *   떨어지는 칼날(역추세 로직)을 잡는 전략의 경우, 거시 경제가 붕괴(예: 코로나, 서브프라임)하는 대폭락장에서 계속 물을 타다 파산할 위험이 있습니다.
   *   **S&P 500의 200일 이동평균선**이 현재가보다 위에 있는 '대세 하락장'에서는 특정 전략의 작동을 원천 강제 차단합니다.
4. **오버나잇 배제 (Timecut)**
   *   단기 돌파 전략이 장기 보유 리스크에 노출되는 것을 막기 위해, 매일 장 종료 직전(오후 3시 15분)에 해당 전략의 잔량을 시장가로 전량 강제 매도합니다.
5. **통신 에러 재시도 방어벽 (Exponential Backoff)**
   *   증권사 서버 점검이나 일시적인 단절(429 Too Many Requests) 시 봇이 꺼지지 않고 대기 간격을 늘려가며 자동 재시도합니다.

---

## ⚙️ 멀티 전략 3대 병렬 아키텍처 (How It Works)

이 봇은 3개의 독립적인 퀀트 전략이 한 계좌 안에서 서로 자금을 빼앗거나 간섭하지 않고 동시에 구동되는 **전략 토너먼트 라우터** 구조를 갖습니다.

1. **데이터 페어링 (Single Data Fetch)**:
   *   1분마다 봇이 동작할 때, API 과부하를 막기 위해 시장 데이터(타겟 종목, S&P 500)를 한 번만 다운로드합니다.
2. **전략 병렬 검사 (Strategy Evaluators)**:
   *   **전략 A (클래식 돌파)**: 래리 윌리엄스 변동성 돌파 타점 계산 + 종가 무조건 청산(Timecut).
   *   **전략 B (하이브리드 돌파)**: 전략 A 로직 + 이동평균선(MA20) 상승장 필터 + 전일 거래량 2배 폭발 필터 적용. (가장 까다롭고 안전한 진입)
   *   **전략 C (낙폭 과대 스윙)**: 대세 상승장 필터(SPY 200MA) + 볼린저 밴드 하단 이탈 + RSI 30 미만 과매도 시 진입.
3. **장부 분리 (Position Isolating)**:
   *   각 전략은 자기만의 예산(`TRADE_AMOUNT_STRAT_A` 등)과 내부 기록 꼬리표(`positions["STRAT_A"]` 등)를 가져, 본인이 산 주식만 관리하고 매도합니다.

---

## 📁 프로젝트 구조 (Directory Structure)

```text
quant_bot/
├── main.py                     # [진입점] 분 단위 백그라운드 스케줄러 실행
├── config.py                   # [설정 센터] API 키, 종목 심볼, 예산 및 방어 파라미터 세팅
├── quant_logic.py              # [핵심 로거] 3개 분할 전략의 매매 조건 및 장부를 관리하는 라우터
├── utils/                      # [기능 모듈 툴박스]
│   ├── broker_api_client.py    # 증권사 API 통신 클라이언트 (재시도 및 주문/취소 담당)
│   ├── market_data.py          # 과거 캔들/지수 데이터 일괄 다운로드 엔진 (yfinance)
│   ├── indicators.py           # Pandas, TA를 확용한 보조지표(RSI, MA, BB 등) 수학 계산기
│   └── logger.py               # 콘솔 출력 및 trading_bot.log 파일 기록 블랙박스
├── .env                        # [보안 파일] 증권사 API 키 관리 (GitHub 업로드 절대 금지)
└── README.md                   # 프로젝트 설명 및 가이드
```

---

## 🚀 시작하기 (Getting Started)

1. **환경 세팅**:
   Python 3.8 이상이 필요합니다. 필수 분석 패키지를 설치합니다.
   ```bash
   pip install requests python-dotenv schedule pandas numpy ta yfinance
   ```
2. **.env 파일 설정**:
   증권사에서 발급받은 API 키를 루트 디렉토리의 `.env` 파일에 기입합니다.
   ```env
   BROKER_API_KEY="본인키"
   BROKER_SECRET_KEY="본인시크릿"
   BROKER_ACCOUNT_ID="계좌번호"
   IS_SIMULATION_MODE="true"
   ```
3. **실행**:
   ```bash
   python main.py
   ```
   *`trading_bot.log` 파일을 통해 봇의 행동을 실시간으로 추적할 수 있습니다.*
