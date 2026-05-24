# 프론트엔드 — 아키텍처 및 구조

Next.js 16 (App Router) 기반 모바일 PWA 대시보드.  
N10-MEW 전략의 포트폴리오 현황, 모멘텀 랭킹, 리밸런싱 상태, 뉴스를 실시간으로 확인합니다.

---

## 실행 명령어

```bash
cd frontend

npm install
npm run dev      # 개발 서버 (http://localhost:3000)
npm run build    # 프로덕션 빌드
npm run lint     # ESLint
```

Node.js >= 20, npm >= 10 필요.

---

## 인증

Supabase Auth 기반 Google OAuth 로그인.

- `middleware.ts` — 모든 경로에 인증 체크 적용. 미인증 사용자는 `/login`으로 리다이렉트
- `/login` — Google 로그인 버튼. 승인된 계정만 접근 가능
- `/auth/callback` — OAuth 콜백 처리 (PKCE flow + implicit flow 모두 지원)
- 로그인 후 헤더 우측 사용자 이메일 표시 + 로그아웃 버튼

---

## 데이터 갱신 주기

| 데이터 | 갱신 주기 | 방식 |
|--------|---------|------|
| 현재가·수익률·평가액·비중 | **5분** | `/api/prices` → Yahoo Finance 직접 호출 |
| 보유 수량·평단가·모멘텀 랭킹 | **15분** | `/api/dashboard` → Supabase 전체 조회 |

5분 인터벌은 현재가만 부분 업데이트 (`setData` 내 가격 관련 필드만 교체).  
15분 인터벌은 전체 상태 교체.

---

## 데이터 흐름

```
Supabase
  └─ GET /api/dashboard (route.ts)            15분 주기
       ├─ portfolio_snapshots (최신 1건)
       ├─ momentum_rankings   (최신 1건)
       ├─ rebalance_log       (최신 1건)
       ├─ Yahoo Finance API   (현재가, 60초 서버 캐시)
       └─ inferInceptionDate() → 벤치마크(QQQ·SPY·DIA) 수익률 비교

Yahoo Finance
  └─ GET /api/prices (route.ts)               5분 주기
       └─ 보유 종목 현재가만 반환 (경량)

출금 예약
  └─ GET/POST/DELETE /api/withdrawal (route.ts)
       └─ backend/data/withdrawal_reservation.json 읽기/쓰기
```

프론트엔드는 Supabase를 직접 호출하지 않고 Route Handler를 통해서만 데이터를 가져옵니다.

---

## 탭 구성 (5탭)

### 1. 개요 탭
- 포트폴리오 요약 카드 (총 자산, 수익률, 현금 잔고)
- 퀵스탯 3개 — 수익률 / QQQ 대비 초과수익(α) / 다음 리밸런싱 날짜
- 모멘텀 Top 5 칩 — 보유 종목 파란색 구분
- 실적 발표 예정 알림 (7일 이내 D-day 표시)
- **출금 예약 카드** — 다음 리밸런싱 시 출금 금액 예약 (% 또는 $ 입력)
- 랭킹 이탈 경보 배너

### 2. 보유종목 탭
- 종목별 수량·평단가·현재가·평가금액·수익률·비중
- 비중 컬러 바 (수익 초록 / 손실 빨강)

### 3. 모멘텀 탭
- 모멘텀 Top 14 랭킹
- 편입 종목 '보유' 배지 표시

### 4. 리밸런싱 탭
- 마지막/다음 리밸런싱 날짜, D-day
- 포트폴리오 건강 상태 배지
- QQQ·SPY·DIA 벤치마크 수익률 비교 바

### 5. 뉴스 탭
- 보유 종목별 + 시장 전반 한국어 뉴스 (네이버 뉴스 기반)
- 감성 분류 (호재·악재·중립)
- 필터 칩 (전체·보유종목·시장)
- 앱 내 기사 본문 하단 시트 모달

---

## API 라우트

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/api/dashboard` | GET | Supabase 전체 데이터 + Yahoo Finance 현재가 + 벤치마크 |
| `/api/prices` | GET | 보유 종목 Yahoo Finance 현재가만 반환 (5분 주기 경량) |
| `/api/news` | GET | 네이버 뉴스 검색 → 종목별 한국어 뉴스 |
| `/api/news/article` | GET | 기사 본문 크롤링 |
| `/api/withdrawal` | GET·POST·DELETE | 출금 예약 조회·설정·취소 |

---

## 컴포넌트 구조

```
src/
├── app/
│   ├── page.tsx                   # 메인 — 탭 라우팅, 이중 갱신 인터벌, 인증 체크
│   ├── layout.tsx                 # PWA 메타태그, 폰트, 전역 스타일
│   ├── globals.css                # Tailwind, iOS safe-area, 모달 애니메이션
│   ├── login/page.tsx             # Google OAuth 로그인 페이지
│   ├── auth/callback/page.tsx     # OAuth 콜백 처리 (PKCE + implicit flow)
│   └── api/
│       ├── dashboard/route.ts     # Supabase + Yahoo Finance + 벤치마크
│       ├── prices/route.ts        # Yahoo Finance 현재가 (5분 주기 경량)
│       ├── news/route.ts          # 네이버 뉴스
│       ├── news/article/route.ts  # 기사 본문 크롤링
│       └── withdrawal/route.ts    # 출금 예약 CRUD
├── components/
│   ├── PortfolioSummary.tsx       # 포트폴리오 요약 카드
│   ├── HoldingsList.tsx           # 보유 종목 목록
│   ├── MomentumRanking.tsx        # 모멘텀 랭킹 리스트
│   ├── RebalanceStatus.tsx        # 리밸런싱 현황 + 벤치마크 비교
│   ├── NewsPage.tsx               # 뉴스 피드
│   ├── NewsDetailModal.tsx        # 뉴스 상세 모달
│   ├── WithdrawalReservation.tsx  # 출금 예약 카드 + 모달
│   ├── BrokerSettings.tsx         # 브로커 API 키 설정 패널
│   └── BottomNav.tsx              # 하단 탭 네비게이션
├── lib/
│   ├── types.ts                   # TypeScript 인터페이스
│   ├── api.ts                     # API 응답 정규화 + fetchLivePrices
│   ├── supabase.ts                # Supabase 브라우저 클라이언트
│   ├── supabase-server.ts         # Supabase 서버 클라이언트 (Route Handler 전용)
│   └── mockData.ts                # API 실패 시 폴백 데이터
└── middleware.ts                  # 인증 미들웨어 — 미인증 시 /login 리다이렉트
```

---

## 기술 스택

| 항목 | 내용 |
|------|------|
| 프레임워크 | Next.js 16 (App Router) |
| 스타일링 | Tailwind CSS v4 |
| 아이콘 | Lucide React |
| 언어 | TypeScript |
| 인증 | Supabase Auth (Google OAuth) |
| 데이터 | Supabase + Yahoo Finance |
| 배포 | Vercel (main/master push 시 자동 배포) |

---

## 환경 변수

```env
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
```

- `NEXT_PUBLIC_*` — 브라우저/미들웨어에서 Supabase Auth에 사용
- `SUPABASE_SERVICE_ROLE_KEY` — 서버 사이드 Route Handler에서만 사용

---

## PWA 설치 (iPhone)

1. Safari에서 `http://<서버IP>:3000` 접속
2. 하단 공유 버튼 → **홈 화면에 추가**
3. 앱 아이콘으로 실행 — 풀스크린 모드로 동작

---

## 현재 진행상황

- [x] Google OAuth 로그인 (Supabase Auth — 승인된 계정만 접근)
- [x] 인증 미들웨어 (미인증 사용자 /login 리다이렉트)
- [x] 5탭 모바일 PWA 대시보드 구현 완료
- [x] 이중 갱신 인터벌 (5분 현재가 / 15분 전체 데이터)
- [x] `/api/prices` 경량 엔드포인트 (5분 주기 현재가 전용)
- [x] 출금 예약 카드 + 모달 UI (% / $ 토글, 미리보기)
- [x] 실적 발표 D-day 알림 카드
- [x] 뉴스 탭 (네이버 뉴스 + 앱 내 기사 본문)
- [x] QQQ·SPY·DIA 벤치마크 수익률 비교 바
- [x] 브로커 API 설정 패널 (`user_broker_credentials` Supabase 저장)
- [x] Vercel 자동 배포 (main/master push 트리거)
- [ ] 실거래 연동 시 실시간 체결 데이터 반영 확인 필요
