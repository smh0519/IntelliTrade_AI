# 📈 IntelliTrade AI - Advanced Quant Trading Bot

이 프로젝트는 Python 기반의 자동 매매 시스템으로, 하이브리드 멀티 전략(Multi-Strategy) 병렬 처리, 강력한 자산 방어 기제(Risk Management), 최우량주 AI 동적 스캐닝(Daily Screener) 기술, 그리고 **미국 증시와 100% 동기화되는 안전한 실시간 모의투자(Paper Trading) 인프라** 및 **텔레그램 모바일 알림망**을 갖춘 완벽한 실전형 퀀트 봇입니다.

---

## 🌟 핵심 신기능 (Recent Updates)

### 🚀 1. 프리마켓 AI 정찰병 (Daily Pre-Market Screener)
과거 단일 종목 감시의 한계를 벗어나, 다중 타겟 자동 스캐닝 아키텍처를 도입했습니다.
* **우량주 유니버스 스캔**: 매일 장 시작 전(또는 봇 가동 시) 나스닥/S&P 핵심 대형주 30개의 최근 60일 치 차트를 일괄 다운로드하여 점수를 매깁니다.
* **Top 5 정밀 타기팅**: 최근 가격 변동성(돌파 매매용) 및 RSI 과매도(역추세 스윙용) 강도를 분석하여 **"오늘 가장 성공 확률이 높은 타겟 주식 5개"**를 매일매일 자동으로 선별 후 메인 감시 모듈에 투입합니다.

### 📱 2. 스마트폰 텔레그램 푸시 알림 (Telegram Integration)
봇이 하루 종일 모니터 화면에 찍어대는 잡다한 로그를 넘어, 사용자의 폰으로 결정적인 순간을 생중계합니다.
* **매매 체결 보고**: 매수 성공 시 또는 시간제한으로 전량 강제 매도 시 수익률과 단가를 즉시 푸시 알림으로 보냅니다.
* **AI 긴급 셧다운 경보**: Claude LLM이 폭락 악재 뉴스를 감지하여 봇을 차단하는 최초의 1회 시점에 폰으로 긴급 진동 알림을 전송합니다.

### 📉 3. 기계적 자율 청산 파이프라인 (Dynamic TP/SL)
물린 주식을 멍하니 장기 투자하지 않습니다. 전략별 철학에 맞춘 수익/위험 한도(%)를 설정하여 감정 없는 확정 매도를 집행합니다.
* **STRAT_A (돌파)**: 익절 상한선 5% / 손절 3%
* **STRAT_B (추세)**: 익절 상한선 8% / 손절 4%
* **STRAT_C (스윙)**: 익절 상한선 4% / 손절 2%
* 전략별 도달 퍼센트는 `config.py` 에서 언제든 쉽게 변경할 수 있습니다.

---

## 🔥 기본 코어 기능 (Core Engines)

### 1. 실시간 페이퍼 트레이딩 엔진 (Zero-Risk Simulation)
내 소중한 돈을 당장 넣을 필요가 없습니다. 봇 내부에 탑재된 '가상 장부 엔진'이 시장의 현재 가격을 실시간으로 추적하며 가상 매매를 진행합니다.
* 리얼타임 가격 동기화 (`yfinance` 라이브 시세) 및 0.05%의 슬리피지(Slippage) 페널티 계산.
* 영구 상태 보존: `JSON` 장부 파일을 통해 언제 껐다 켜도 1만 달러 계좌 상태를 그대로 불러옵니다.

### 2. 계층형 포트폴리오 대시보드 (CLI Dashboard)
1분마다 스캔된 5개의 타겟 주식들의 3가지 전략별 타점 검사 결과를 우아한 표 형태로 터미널에 그려줍니다.
* `[전략 A] -> [애플] -> [150달러 평단가로 5주 매수]`와 같이 철저하게 분리되어 어느 로직이 돈을 벌어주는지 추적합니다.

### 3. 멀티 전략 3대 병렬 라우터
* **[STRAT_A] 래리 윌리엄스 돌파 (Classic)**: 변동성 돌파 타점 계산 + 당일 타임컷 강제 청산.
* **[STRAT_B] 하이브리드 추세 돌파**: 상승장 20일선 기준 + 전일 거래량 폭발 조건 충족 시 진입.
* **[STRAT_C] 낙폭 과대 스윙**: 대세 상승장(`SPY` 200MA) 방어필터 + 볼린저 밴드 하단 및 RSI 30 미만 돌입 시 역추세 매수.

---

## 🛡 실전형 방어 가이드라인 (Defense Mechanisms)

1. **오버나잇 배제 (Timecut)**: STRAT_A의 종목을 뉴욕 시각 오후 3시 55분에 강제 시장가 청산.
2. **AI 뉴스 마크맨 (Claude LLM)**: 1시간마다 Claude AI가 구글 영어 기사를 요약/판별하여 치명적 악재 발생 시 방어벽 전개.
3. **대세 하락장 접근 금지 (Macro Filter Lock-on)**: S&P 500(`SPY`) 하락 추세 시 역추세 로직 동결.

---

## 📁 프로젝트 구조 (Directory Structure)

```text
quant_bot/
├── main.py                     # [진입점] 프리마켓 스캐너 구동 및 분 단위 퀀트 라우터 가동
├── config.py                   # [설정 센터] 감시 우량주 유니버스(30개) 및 익절/손절(TP/SL) 파라미터 제어
├── quant_logic.py              # [핵심 엔진] 5개 멀티 타겟 순회, TP/SL 수익률 검사 및 트리형 대시보드 렌더링
├── claude_assistant.py         # [AI 어시스턴트] Claude 기반 대화형 퀀트 개발 어시스턴트 CLI
├── config/
│   └── settings.py             # [보조 설정] API 키, 로그 경로, 백테스팅 등 확장 설정 관리
├── data/
│   └── mock_account.json       # [가상 장부] 시뮬레이션용 데이터베이스 파일
├── utils/                      
│   ├── screener.py             # [인공지능 스캐너] 장 시작 전 60일치 일봉을 긁어 Top 5 사냥감 추출
│   ├── telegram_bot.py         # [알림 모듈] 텔레그램 푸시 알람 발송기
│   ├── notifier.py             # [통합 알림] 슬랙 + 텔레그램 멀티채널 알림 클래스
│   ├── mock_account.py         # 실시간 물타기 로직이 들어간 가상 DB 제어기
│   ├── ai_news_filter.py       # [LLM 모듈] 최신 뉴스 텍스트를 읽고 악재 여부를 판단 (Claude)
│   ├── broker_api_client.py    # 통신 연결망 (가상 모드 라우팅 포함)
│   ├── market_data.py          # 과거 캔들 데이터 엔진
│   ├── indicators.py           # RSI, MA, BB 등 수학적 보조지표 계산 모듈
│   └── logger.py               # 콘솔 출력 및 로그 백업 모듈
└── .env                        # [보안 파일] API Key, 텔레그램 토큰 및 IS_SIMULATION_MODE 세팅
```

---

## 🚀 시작하기 (How to Run)

1. **필수 패키지 설치**:
   ```bash
   pip install requests python-dotenv schedule pandas numpy ta yfinance anthropic pykrx pytz rich
   ```

2. **환경 변수 세팅 (`.env`)**:
   텔레그램 알림 봇 연동 및 Anthropic(Claude) API 세팅, 모의투자 모드를 활성화합니다.
   ```env
   IS_SIMULATION_MODE="true"
   ANTHROPIC_API_KEY="본인키"
   TELEGRAM_BOT_TOKEN="봇토큰"
   TELEGRAM_CHAT_ID="채팅숫자아이디"
   ```

3. **로봇 부팅 (Startup)**:
   ```bash
   python main.py
   ```
   *시작 시 스마트폰 텔레그램으로 "가동 시작" 문자가 전송되며 터미널에 오늘의 추천 종목 Top 5 대시보드가 그려집니다.*
