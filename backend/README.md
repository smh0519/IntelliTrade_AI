# 📈 IntelliTrade AI — N10-MEW Quant Trading Bot

이 프로젝트는 Python 기반의 자동 매매 시스템으로, **나스닥 100 모멘텀 동일가중(N10-MEW) 전략**을 중심으로 월간 포트폴리오 리밸런싱, Physical AI 테마 우대 선별, 실시간 모의투자(Paper Trading) 인프라, 그리고 텔레그램 모바일 알림망을 갖춘 실전형 퀀트 봇입니다.

---

## 🧠 핵심 전략: N10-MEW (Nasdaq 10 Momentum Equal Weight)

| 항목 | 내용 |
|---|---|
| **유니버스** | 나스닥 100 시가총액 상위 50개 우량주 |
| **선정 신호** | 최근 3개월(63영업일) 수익률 상위 10개 종목 |
| **자산 배분** | 선정 종목 각 10% 동일가중 |
| **핵심 테마** | Physical AI (모멘텀 상위권에 자연 편입) |
| **정기 리밸런싱** | 매월 첫 영업일 오전 10:00 (뉴욕 기준) |
| **즉시 교체** | 보유 종목이 12위 밖으로 이탈 시 자동 교체 |

---

## 🌟 주요 기능 (Feature Overview)

### 📊 1. 3개월 모멘텀 스크리너 (Momentum Screener)
매 시간 유니버스 50개 종목의 63일 수익률을 일괄 계산하여 실시간으로 랭킹을 갱신합니다.

- `yfinance` 배치 다운로드로 50개 종목을 단일 연결로 처리 (속도 최적화)
- 모멘텀 = `(현재가 / 63영업일 전 가격) - 1`
- Physical AI 보너스 반영 후 내림차순 정렬 → Top 12 반환 (포트폴리오 10 + 이탈 감지 버퍼 2)

### 🔄 2. 월간 리밸런싱 엔진 (N10MEWRebalancer)
3단계 집행 파이프라인으로 정확한 비중 조정을 수행합니다.

```
1단계 — 탈락 종목 전량 매도   (현금 먼저 확보)
2단계 — 잔류 종목 과비중 조정  (2% 오차 기준)
3단계 — 신규·과소비중 종목 매수
```

- **정기 트리거**: 매월 첫 영업일 (토→월, 일→월 자동 보정)
- **이탈 트리거**: 보유 종목이 실시간 랭킹 12위 밖으로 밀리면 즉시 교체
- 집행 후 텔레그램으로 새 포트폴리오 구성 및 거래 내역 즉시 보고

### 📱 3. 텔레그램 실시간 알림
결정적인 이벤트를 스마트폰으로 즉시 수신합니다.

- **리밸런싱 완료**: 새 포트폴리오 Top 10 목록 + 매도/매수 내역
- **랭킹 이탈 경보**: 즉시 교체 사유 및 진행 상황
- **포트폴리오 손실 경고**: 전체 수익률 -20% 도달 시 긴급 알림
- **AI 뉴스 경보**: 매주 월요일 편입 종목 악재 점검 (Claude LLM)

### 📉 4. 실시간 페이퍼 트레이딩 (Zero-Risk Simulation)
실 자금 없이 전략 성능을 검증합니다.

- `yfinance` 실시간 시세 기반 가상 체결 (슬리피지 0.05% 적용)
- `JSON` 장부로 영구 상태 보존 — 재시작 시 그대로 복원
- 초기 자본금 $10,000, `data/mock_account.json`으로 관리

### 🗄️ 5. Supabase 데이터 적재
전략 실행 결과를 Supabase로 적재해 프론트엔드 대시보드에서 조회할 수 있습니다.

- 포트폴리오 스냅샷 저장: `portfolio_snapshots`
- 모멘텀 랭킹 저장: `momentum_rankings`
- 리밸런싱 이벤트 로그 저장: `rebalance_log`
- 체결 거래 로그 저장: `trade_logs`

---

## 🛡 리스크 관리 (Defense Mechanisms)

| 항목 | 내용 |
|---|---|
| **포트폴리오 손실 경고** | 전체 평가손 -20% 도달 시 텔레그램 긴급 알림 |
| **랭킹 이탈 자동 교체** | 12위 밖 이탈 종목은 다음 사이클에 즉시 청산 |
| **비중 조정 임계값** | 2% 미만 오차는 거래 생략 (불필요한 수수료 방지) |
| **AI 뉴스 마크맨** | 매주 월요일 Claude AI가 편입 종목 악재 뉴스 분석 |
| **집행 시간 제어** | 개장 30분 후(10:00)부터 장 마감 전까지만 리밸런싱 집행 |

---

## 📁 프로젝트 구조 (Directory Structure)

```text
backend/
├── main.py                     # [진입점] 1시간 주기 전략 실행, 주간 뉴스 점검 스케줄
├── config.py                   # [설정 센터] 유니버스 50개, N10-MEW 파라미터, Physical AI 화이트리스트
├── quant_logic.py              # [전략 핸들러] 랭킹 산출·리밸런싱 트리거·대시보드 렌더링
├── rebalancer.py               # [리밸런싱 엔진] 월간/이탈 트리거 판단 및 3단계 거래 집행
├── backtest.py                 # [백테스트] N10-MEW 성과 검증 스크립트
├── setup_supabase.py           # [DB 준비] Supabase 테이블 초기화/검증 스크립트
├── seed_supabase.py            # [DB 시드] 초기 샘플 데이터 적재 스크립트
├── supabase_schema.sql         # [DB 스키마] Supabase 테이블 정의 SQL
├── config/
│   └── settings.py             # [보조 설정] API 키, 로그 경로 등 확장 설정
├── data/
│   └── mock_account.json       # [가상 장부] N10_MEW 버킷 기반 시뮬레이션 DB
├── utils/
│   ├── screener.py             # [모멘텀 스크리너] 63일 수익률 기반 Top 12 랭킹 산출
│   ├── telegram_bot.py         # [알림 모듈] 텔레그램 푸시 알림/명령 처리
│   ├── mock_account.py         # [가상 DB] N10_MEW 포지션 장부 제어
│   ├── ai_news_filter.py       # [LLM 모듈] Claude AI 기반 악재 뉴스 판별
│   ├── broker_api_client.py    # [브로커 클라이언트] 실거래 및 가상 모드 라우팅
│   ├── supabase_client.py      # [DB 클라이언트] 스냅샷/랭킹/거래 로그 저장
│   ├── market_data.py          # [데이터 엔진] 과거 캔들 데이터 수집
│   ├── indicators.py           # [보조지표] RSI, MA, 볼린저 밴드 등 계산 모듈
│   └── logger.py               # [로거] 콘솔 출력 및 로그 파일 백업
└── requirements.txt            # [의존성] 백엔드 패키지 목록
```

---

## 🚀 시작하기 (How to Run)

**1. 필수 패키지 설치**

```bash
pip install -r requirements.txt
```

**2. 환경 변수 설정 (`.env`)**

```env
IS_SIMULATION_MODE="true"
ANTHROPIC_API_KEY="본인키"
TELEGRAM_BOT_TOKEN="봇토큰"
TELEGRAM_CHAT_ID="채팅숫자아이디"
BROKER_API_KEY="브로커키"
BROKER_SECRET_KEY="브로커시크릿"
BROKER_ACCOUNT_ID="계좌번호"
SUPABASE_URL="https://xxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="서비스롤키"
```

**3. 봇 실행**

```bash
python main.py
```

시작 시 텔레그램으로 부팅 완료 알림이 전송되고, 즉시 유니버스 50개 종목의 모멘텀 랭킹을 산출합니다.  
이후 **1시간마다** 랭킹을 갱신하며, 매월 첫 영업일 오전 10시에 자동으로 리밸런싱이 집행됩니다.

---

## ⚙️ 주요 파라미터 커스터마이징 (`config.py`)

| 파라미터 | 기본값 | 설명 |
|---|---|---|
| `MOMENTUM_PERIOD_DAYS` | `63` | 모멘텀 계산 기간 (영업일 기준) |
| `TOP_N_PORTFOLIO` | `10` | 포트폴리오 편입 종목 수 |
| `REBALANCE_EXIT_RANK` | `12` | 이 순위 밖 이탈 시 즉시 교체 |
| `WEIGHT_PER_STOCK` | `0.10` | 종목당 동일 비중 |
| `REBALANCE_THRESHOLD` | `0.02` | 비중 조정 최소 오차 기준 |
| `PORTFOLIO_STOP_LOSS` | `-0.20` | 전체 포트폴리오 경고 손실률 |

---

## ✅ 현재 진행상황 (Progress)

- N10-MEW 핵심 전략 루프(`main.py` + `quant_logic.py`) 구현 완료
- 월간/이탈 기반 리밸런싱 엔진(`rebalancer.py`) 구현 완료
- 모의투자 장부(`data/mock_account.json`) 기반 페이퍼 트레이딩 동작
- 텔레그램 알림 및 명령 제어(시작/중지/상태 확인) 연동 완료
- Supabase 적재 파이프라인(`utils/supabase_client.py`) 및 스키마 파일 구성 완료
- 백테스트 스크립트(`backtest.py`)와 결과 이미지(`backtest_result.png`) 포함
- 실거래 브로커 API 상세 구현/운영 환경 검증은 추가 작업 단계
