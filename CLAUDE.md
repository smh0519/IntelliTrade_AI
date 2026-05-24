# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 규칙

- 항상 한국어로 답변
- 작업 전 수행 단계를 기획하여 사용자에게 보여주고 확인 받을 것
- 정확하지 않은 정보는 웹 검색 후 답변
- 기능별로 파일을 분리하고, 새 기능은 새 파일/모듈로 작성
- 기존 함수 시그니처 변경 금지
- 기능 수정·추가 시 동작 여부 확인 후 완료 보고
- README 파일을 현재 진행상황에 맞게 업데이트

---

## 프로젝트 개요

**IntelliTrade AI — N10-MEW** : 나스닥 100 모멘텀 동일가중 자동 매매 시스템.

- **Backend** (`backend/`): Python 봇. 1시간마다 모멘텀 랭킹 산출 → 리밸런싱 집행 → Supabase 적재
- **Frontend** (`frontend/`): Next.js 16 + Tailwind v4 대시보드. Supabase에서 데이터 읽어 포트폴리오 현황 표시
- **문서** (`docs/`): 전체 프로젝트 문서 (BACKEND.md, FRONTEND.md, MOMENTUM_STRATEGY.md, CONTRIBUTING.md)

---

## 명령어

### Backend

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

### Frontend

```bash
cd frontend

npm install
npm run dev      # 개발 서버 (http://localhost:3000)
npm run build    # 프로덕션 빌드
npm run lint     # ESLint
```

---

## 아키텍처

### 실행 흐름

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
                 ├─ [2] 과비중 조정 매도
                 └─ [3] 소수점 매수 (가용현금 / 1.0005 내 최대)
                      └─ mock_account.py (슬리피지 0.05% 적용)
```

### 리밸런싱 트리거 3가지

| 트리거 | 조건 |
|--------|------|
| 초기 구성 | 보유 종목 없음 → 즉시 강제 실행 |
| 월간 정기 | 매월 첫 영업일 + 09:30 AM (뉴욕) + 이번 달 미실행 |
| 랭킹 이탈 | 보유 종목이 12위(`REBALANCE_EXIT_RANK`) 밖으로 이탈 |

### 브로커 모드 분기

`IS_SIMULATION_MODE=true`(기본값)이면 실제 API 호출 없이 `data/mock_account.json` 장부를 사용한다.
실거래 모드로 전환하려면 `.env`에서 `IS_SIMULATION_MODE=false`로 변경 후 브로커 API 키 설정.

### 가상 장부 구조 (`data/mock_account.json`)

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

포지션은 전략 태그(`N10_MEW`) 단위로 버킷 구분. `execute_virtual_buy` / `execute_virtual_sell`이 평단가 가중평균을 자동 계산.

### Supabase 테이블

| 테이블 | 저장 주기 | 내용 |
|--------|----------|------|
| `portfolio_snapshots` | 매 1시간 | 현금·평가액·포지션 스냅샷 |
| `momentum_rankings` | 매 1시간 | Top 14 모멘텀 랭킹 + 편입 여부 |
| `rebalance_log` | 리밸런싱 시 | 사유·매도·매수 종목 목록 |
| `trade_log` | 거래 시 | 개별 체결 내역 |
| `earnings_calendar` | 매 1시간 | 보유 종목 실적 발표일 |

### Frontend 데이터 흐름

```
Supabase
  └─ GET /api/dashboard (route.ts)     15분 주기
       ├─ portfolio_snapshots (최신 1건)
       ├─ momentum_rankings   (최신 1건)
       ├─ rebalance_log       (최신 1건)
       ├─ Yahoo Finance API   (현재가, 60초 서버 캐시)
       └─ inferInceptionDate() → 벤치마크(QQQ·SPY·DIA) 수익률 비교

Yahoo Finance
  └─ GET /api/prices (route.ts)        5분 주기
       └─ 보유 종목 현재가만 반환 (경량)

출금 예약
  └─ GET/POST/DELETE /api/withdrawal (route.ts)
       └─ backend/data/withdrawal_reservation.json 읽기/쓰기
```

프론트엔드는 Supabase를 직접 쓰지 않고 Route Handler를 통해서만 데이터를 가져온다.

### 핵심 파라미터 (`backend/config.py`)

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `MOMENTUM_PERIOD_DAYS` | `63` | 모멘텀 계산 기간 (영업일) |
| `TOP_N_PORTFOLIO` | `10` | 편입 종목 수 |
| `REBALANCE_EXIT_RANK` | `12` | 이탈 감지 순위 임계값 |
| `WEIGHT_PER_STOCK` | `0.10` | 종목당 동일 비중 |
| `REBALANCE_THRESHOLD` | `0.02` | 비중 조정 최소 오차 |
| `REBALANCE_EXECUTION_TIME` | `"09:30"` | 집행 시각 (뉴욕, 정규장 개장 즉시) |
| `PORTFOLIO_STOP_LOSS` | `-0.20` | 전체 포트폴리오 경고 손실률 |

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

프론트엔드는 `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`만 사용 (서버 사이드 Route Handler에서만).

---

## 전략 문서

전략 분석 및 개선 계획은 `docs/MOMENTUM_STRATEGY.md` 참조.  
전체 문서 목록은 `docs/README.md` 참조.
