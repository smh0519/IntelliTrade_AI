# 백엔드 — 아키텍처 및 구조

## 실행 명령어

```bash
cd backend

# 패키지 설치
pip install -r requirements.txt

# 봇 실행 (1시간 주기 무한 루프 + Telegram 폴링)
python main.py

# 전략 1회 실행 (GitHub Actions / 테스트용)
python run_once.py

# 뉴스 악재 점검 1회 실행
python run_once.py --news

# 날짜 조건 무시하고 즉시 리밸런싱 (개발 테스트)
python run_once.py --force-rebalance

# 백테스트
python backtest.py

# Supabase 테이블 초기화
python setup_supabase.py
```

---

## 전략 실행 흐름

```
main.py (매 1시간)
  └─ TradingStrategy.execute_strategy()          # quant_logic.py
       ├─ fetch_nasdaq100_universe()              # utils/universe.py
       │    └─ pytickersymbols → Wikipedia → config.py 폴백
       ├─ run_momentum_screener()                 # utils/screener.py
       │    └─ yfinance 배치 다운로드 → 63일 수익률 계산 → Top 14 반환
       ├─ get_current_price() × 14               # utils/broker_api_client.py
       ├─ render_dashboard() → Supabase 저장      # utils/supabase_client.py
       └─ 리밸런싱 트리거 판단
            └─ N10MEWRebalancer.execute_rebalance()   # rebalancer.py
                 ├─ 출금 예약 확인                     # utils/withdrawal.py
                 ├─ [1] 탈락 종목 전량 매도
                 ├─ [2] 과비중 조정 매도 (±2% 임계값)
                 └─ [3] 소수점 매수 (가용현금 / 1.0005 내 최대)
                      └─ mock_account.py (슬리피지 0.05% 적용)
```

---

## 리밸런싱 트리거

| 트리거 | 조건 |
|--------|------|
| 초기 구성 | 보유 종목 없음 → 즉시 강제 실행 |
| 월간 정기 | 매월 첫 영업일 + 09:30 AM (뉴욕) + 이번 달 미실행 |
| 랭킹 이탈 | 보유 종목이 12위(`REBALANCE_EXIT_RANK`) 밖으로 이탈 |

---

## 유니버스 동적 조회 (`utils/universe.py`)

나스닥 100 구성 종목을 매일 1회 외부에서 조회합니다.

```
1순위: pytickersymbols (주간 GitHub Actions 자동 갱신, Yahoo Finance 형식 티커)
2순위: Wikipedia 스크래핑
3순위: config.py 하드코딩 목록 (폴백)
```

당일 캐시 적용 — 봇이 1시간마다 실행되어도 하루 1회만 외부 요청.

---

## 출금 예약 (`utils/withdrawal.py`)

리밸런싱 시 출금 예약이 있으면:

```
investable = total_value - withdrawal_amount
target_per_stock = investable × WEIGHT_PER_STOCK
→ 과비중 종목 자동 매도로 현금 확보
→ 리밸런싱 완료 후 예약 자동 초기화
```

예약 저장소: `data/withdrawal_reservation.json`

---

## 브로커 모드 분기

`IS_SIMULATION_MODE=true`(기본값) → `data/mock_account.json` 가상 장부 사용  
`IS_SIMULATION_MODE=false` → 실거래 브로커 API 호출 (별도 구현 필요)

---

## 가상 장부 구조 (`data/mock_account.json`)

```json
{
  "initial_cash": 10000.0,
  "cash": 8500.0,
  "currency": "USD",
  "positions": {
    "N10_MEW": {
      "NVDA": { "qty": 1.2345, "avg_price": 890.12 }
    }
  }
}
```

포지션은 전략 태그(`N10_MEW`) 단위로 버킷 구분. 평단가 가중평균 자동 계산.

---

## Supabase 테이블

| 테이블 | 저장 주기 | 내용 |
|--------|----------|------|
| `portfolio_snapshots` | 매 1시간 | 현금·평가액·포지션 스냅샷 |
| `momentum_rankings` | 매 1시간 | Top 14 모멘텀 랭킹 + 편입 여부 |
| `rebalance_log` | 리밸런싱 시 | 사유·매도·매수 종목 목록 |
| `trade_log` | 거래 시 | 개별 체결 내역 |
| `earnings_calendar` | 매 1시간 | 보유 종목 실적 발표일 |

---

## 핵심 파라미터 (`config.py`)

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `MOMENTUM_PERIOD_DAYS` | `63` | 모멘텀 계산 기간 (영업일) |
| `TOP_N_PORTFOLIO` | `10` | 편입 종목 수 |
| `REBALANCE_EXIT_RANK` | `12` | 이탈 감지 순위 임계값 |
| `WEIGHT_PER_STOCK` | `0.10` | 종목당 동일 비중 |
| `REBALANCE_THRESHOLD` | `0.02` | 비중 조정 최소 오차 |
| `REBALANCE_EXECUTION_TIME` | `"09:30"` | 집행 시각 (뉴욕, 정규장 개장 즉시) |
| `PORTFOLIO_STOP_LOSS` | `-0.20` | 전체 포트폴리오 경고 손실률 |
| `MIN_CASH_BALANCE` | `500` | 리밸런싱 후 유지할 최소 현금 ($) |

---

## 환경 변수 (`.env`)

```env
IS_SIMULATION_MODE=true
ANTHROPIC_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
BROKER_API_KEY=...          # 실거래 모드에서만 필요
BROKER_SECRET_KEY=...
BROKER_ACCOUNT_ID=...
```

---

## 파일 구조

```
backend/
├── main.py                  # 진입점 — 1시간 주기 스케줄러 + Telegram 폴링
├── config.py                # 전략 파라미터, 유니버스 폴백 목록
├── quant_logic.py           # 전략 핸들러 — 랭킹·트리거·대시보드
├── rebalancer.py            # 리밸런싱 엔진 — 3단계 매매 집행
├── backtest.py              # 백테스트 스크립트
├── run_once.py              # 단발 실행 (GitHub Actions용)
├── setup_supabase.py        # Supabase 테이블 초기화
├── data/
│   ├── mock_account.json    # 가상 장부
│   └── withdrawal_reservation.json  # 출금 예약 상태
└── utils/
    ├── screener.py          # 모멘텀 스크리너 (63일 수익률 Top 14)
    ├── universe.py          # 나스닥 100 동적 유니버스 조회
    ├── withdrawal.py        # 출금 예약 관리
    ├── broker_api_client.py # 브로커 클라이언트 (시뮬/실거래 분기)
    ├── mock_account.py      # 가상 장부 제어
    ├── supabase_client.py   # Supabase 데이터 적재
    ├── telegram_bot.py      # 텔레그램 알림/명령
    ├── ai_news_filter.py    # Claude AI 악재 뉴스 판별
    ├── earnings.py          # 실적 발표일 조회
    ├── indicators.py        # 기술 지표 계산
    ├── market_data.py       # 과거 데이터 수집
    ├── bot_state.py         # 봇 상태 관리 (활성/일시정지/긴급정지)
    ├── notifier.py          # 알림 유틸
    └── logger.py            # 로거
```

---

## 현재 진행상황

- [x] N10-MEW 전략 루프 구현 완료
- [x] 나스닥 100 유니버스 동적 조회 (pytickersymbols 기반)
- [x] 3단계 리밸런싱 엔진 구현 완료
- [x] 소수점 매매 + 슬리피지 선반영 로직 적용
- [x] 출금 예약 기능 구현 완료
- [x] 텔레그램 알림/명령 연동 완료
- [x] Supabase 적재 파이프라인 완료
- [x] 백테스트 스크립트 포함
- [ ] 실거래 브로커 API 연동 (추가 작업 예정)
