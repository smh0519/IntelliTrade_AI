# IntelliTrade AI — N10-MEW

나스닥 100 모멘텀 동일가중(N10-MEW) 전략 기반 자동 매매 시스템.

Python 백엔드 봇 + Next.js 모바일 대시보드로 구성됩니다.

---

## 전략 요약

| 항목 | 내용 |
|------|------|
| 유니버스 | 나스닥 100 시가총액 상위 50 종목 |
| 선정 신호 | 최근 3개월(63영업일) 수익률 상위 10개 |
| 자산 배분 | 동일비중 10% |
| 리밸런싱 | 매월 첫 영업일 09:30 AM (뉴욕, 정규장 개장) |
| 안전벨트 | QQQ 200일 이동평균 기반 시장 국면 필터 |

---

## 문서 목록

| 문서 | 설명 |
|------|------|
| [BACKEND.md](./BACKEND.md) | 백엔드 아키텍처, 실행 명령어, 파라미터 |
| [FRONTEND.md](./FRONTEND.md) | 프론트엔드 구조, 컴포넌트, 데이터 흐름 |
| [MOMENTUM_STRATEGY.md](./MOMENTUM_STRATEGY.md) | 현재 전략 구현 상태 및 리밸런싱 로직 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 브랜치 전략, 커밋 규칙, 코드 스타일 |

---

## 빠른 시작

```bash
# 백엔드
cd backend
pip install -r requirements.txt
python main.py

# 프론트엔드
cd frontend
npm install
npm run dev
```

---

## 시장 국면 필터 (안전벨트)

QQQ 200일 이동평균 대비 현재가 위치로 4단계 국면을 판단, 단계별로 매매를 제한합니다.

| 국면 | 조건 | 동작 |
|------|------|------|
| 🟢 BULL | QQQ > 200MA × 1.02 | 정상 운용 (매수·매도 모두 허용) |
| 🟡 NEUTRAL | 200MA ± 2% 구간 | 신규 매수 중단, 기존 보유 유지 |
| 🔴 CAUTION | QQQ < 200MA × 0.98 | 탈락 매도만 허용 |
| 🚨 EMERGENCY | QQQ < 200MA × 0.95 | 즉시 70% 청산 → 2거래일 후 나머지 30% 청산 |

**BULL 복귀 조건**: QQQ > 200MA × 1.02 를 5거래일 연속 유지 → 즉시 재진입 리밸런싱 실행

---

## 시스템 구성

```
GitHub Actions (매시 30분, 장중 월~금)
  └─ run_once.py                     # 전략 1회 실행
       └─ mock_account.json 커밋      # 포트폴리오 상태 자동 저장

Backend (Python)
  └─ main.py                         # 1시간 주기 루프 + Telegram 폴링
       ├─ utils/market_filter.py      # QQQ 200MA 국면 판단 (안전벨트)
       ├─ quant_logic.py              # 모멘텀 랭킹 산출 + 리밸런싱 트리거
       ├─ rebalancer.py               # 3단계 매매 집행 + 긴급 청산
       └─ Supabase 적재

Frontend (Next.js PWA)
  └─ Supabase / Yahoo Finance 데이터 조회
       ├─ 5분 주기: 현재가 갱신 (/api/prices)
       └─ 15분 주기: 전체 데이터 갱신 (/api/dashboard)

Vercel (자동 배포)
  └─ main/master 브랜치 push 시 frontend 자동 배포
```

---

## 현재 진행상황

### 백엔드

- [x] N10-MEW 전략 루프 (`main.py` + `quant_logic.py`) 구현 완료
- [x] 나스닥 100 유니버스 동적 조회 (`utils/universe.py`)
  - pytickersymbols → Wikipedia → config.py 폴백 3단계
- [x] 3단계 리밸런싱 엔진 (`rebalancer.py`)
  - 탈락 매도 → 과비중 조정 → 소수점 매수
  - 집행 시각 09:30 AM (뉴욕) 적용
  - 시장 국면에 따라 단계별 선택 실행
- [x] 소수점 매매 + 슬리피지 선반영 (`usable_cash = available_cash / 1.0005`)
- [x] 출금 예약 기능 (`utils/withdrawal.py`)
- [x] 모의투자 장부 (`data/mock_account.json`) 페이퍼 트레이딩
- [x] 텔레그램 알림/명령 연동
- [x] Supabase 적재 파이프라인 (`portfolio_snapshots`, `momentum_rankings`, `rebalance_log`, `trade_log`, `earnings_calendar`)
- [x] GitHub Actions 자동 실행 (`bot.yml` — 장중 매시 30분)
- [x] 백테스트 스크립트 (`backtest.py`)
- [x] 시장 국면 필터 안전벨트 (`utils/market_filter.py`)
  - QQQ 200MA 기반 4단계 국면 판단 (BULL / NEUTRAL / CAUTION / EMERGENCY)
  - EMERGENCY 시 2단계 분할 청산 (즉시 70% → 2거래일 후 30%)
  - BULL 복귀 시 5거래일 확인 후 즉시 재진입 리밸런싱
  - 국면 상태 영속화 (`data/market_state.json`) — 봇 재시작 후에도 유지
- [x] 월간 리밸런싱 단일화 (랭킹 이탈 즉시 교체 제거 — 과도한 매매 비용 방지)
- [ ] 실거래 브로커 API 연동 (추가 작업 예정)

### 프론트엔드

- [x] Google OAuth 로그인 (Supabase Auth — 승인된 계정만 접근)
- [x] 인증 미들웨어 (`middleware.ts` — 미인증 시 /login 리다이렉트)
- [x] 5탭 모바일 PWA 대시보드 (개요 / 보유종목 / 모멘텀 / 리밸런싱 / 뉴스)
- [x] 이중 갱신 인터벌 (5분 현재가 / 15분 전체)
- [x] 출금 예약 카드 + 모달 UI
- [x] 실적 발표 D-day 알림
- [x] 뉴스 탭 (네이버 뉴스 + 감성 분류 + 기사 본문 모달)
- [x] QQQ·SPY·DIA 벤치마크 수익률 비교
- [x] 브로커 API 설정 패널 (`BrokerSettings` — Supabase `user_broker_credentials` 테이블 저장)
- [x] Vercel 자동 배포 (`deploy.yml` — main/master push 시 트리거)
- [ ] 실거래 연동 시 실시간 체결 데이터 반영 확인 필요
