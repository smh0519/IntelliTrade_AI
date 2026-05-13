# IntelliTrade AI — Frontend

IntelliTrade AI 트레이딩 봇의 모바일 대시보드입니다.  
N10-MEW(나스닥 10 모멘텀 동일가중) 전략의 포트폴리오 현황, 모멘텀 랭킹, 리밸런싱 상태를 실시간으로 확인할 수 있는 **Next.js PWA** 앱입니다.

---

## 시작하기

```bash
npm install
npm run dev      # 개발 서버 (http://localhost:3000)
npm run build    # 프로덕션 빌드
```

---

## 폴더 구조

```
frontend/
├── public/
│   └── manifest.json          # PWA 매니페스트 (앱 이름, 아이콘, 테마색)
│
├── src/
│   ├── app/
│   │   ├── layout.tsx          # 루트 레이아웃 (PWA 메타태그, 폰트, 전역 스타일)
│   │   ├── page.tsx            # 메인 페이지 (탭 라우팅 및 전체 화면 조합)
│   │   └── globals.css         # 전역 CSS (Tailwind import, iOS safe-area 유틸)
│   │
│   ├── components/
│   │   ├── PortfolioSummary.tsx  # 포트폴리오 요약 카드 (총 자산, 수익률, 현금)
│   │   ├── HoldingsList.tsx      # 보유 종목 목록 (종목별 수익률, 비중 바)
│   │   ├── MomentumRanking.tsx   # 모멘텀 랭킹 리스트 (63일 기준 Top 12)
│   │   ├── RebalanceStatus.tsx   # 리밸런싱 현황 + 지수 비교 바
│   │   └── BottomNav.tsx         # 하단 탭 네비게이션
│   │
│   └── lib/
│       ├── types.ts              # 공용 TypeScript 인터페이스 정의
│       └── mockData.ts           # 개발용 목데이터 (실제 연동 전 사용)
│
├── NEXTJS_SETUP.md             # Next.js 기본 설정 및 Vercel 배포 가이드
├── package.json
└── tsconfig.json
```

---

## 페이지 구성 및 기능

앱은 **하단 탭 4개**로 구성되며, 단일 페이지(`page.tsx`) 안에서 탭 전환으로 동작합니다.

### 1. 개요 탭 (Overview)

전체 포트폴리오 상황을 한눈에 파악하는 홈 화면입니다.

- **포트폴리오 요약 카드** — 총 자산($), 초기자본 대비 전체 수익률(%), 현금 잔고, 보유 종목 수
- **퀵스탯 3개** — 수익률 / QQQ 대비 초과수익(α) / 다음 리밸런싱 날짜
- **모멘텀 Top 5 칩** — 현재 모멘텀 상위 5개 종목을 태그로 표시, 보유 중인 종목은 파란색으로 구분
- **랭킹 이탈 경보 배너** — 보유 종목이 12위 밖으로 이탈했을 때 경고 배너 노출

---

### 2. 보유종목 탭 (Holdings)

현재 편입된 종목 전체를 상세하게 확인합니다.

- 종목별 **수량(주)**, **평균 매수가**, **현재가**, **평가금액**
- **수익률(%)** 및 **포트폴리오 비중(%)** 표시
- 왼쪽 컬러 바 — 수익이면 초록, 손실이면 빨강으로 비중 시각화
- 평가금액 기준 내림차순 정렬

---

### 3. 모멘텀 탭 (Momentum)

스크리너가 산출한 63일 모멘텀 랭킹 전체를 보여줍니다.

- 유니버스 50개 종목 중 **Top 12** 순위 표시
- 각 종목의 **63일 수익률(%)** 을 가로 바 차트로 시각화
- 현재 포트폴리오에 편입된 종목에 **'보유'** 배지 표시
- 파란 배경으로 보유 종목을 비보유 종목과 시각적으로 구분

---

### 4. 리밸런싱 탭 (Rebalance)

리밸런싱 일정과 지수 대비 성과를 확인합니다.

- **마지막 리밸런싱 날짜** / **다음 리밸런싱 날짜** (D-day 표시)
- **포트폴리오 건강 상태** — 이탈 종목 없으면 초록 배지, 이탈 감지 시 주황 경고
- **지수 비교 바** — 전략 수익률 vs QQQ(나스닥 100) / SPY(S&P 500) / DIA(다우존스)

---

## 데이터 흐름

```
현재 (개발 단계)
  mockData.ts  →  page.tsx  →  각 컴포넌트

향후 (Supabase 연동 후)
  Python 봇 (backend/)
    └─ 매 1시간마다 실행
    └─ 거래 결과를 Supabase PostgreSQL에 저장
  
  Next.js (frontend/)
    └─ Supabase Client로 실시간 데이터 fetch
    └─ page.tsx의 mockData → API 호출로 교체
```

---

## PWA 설치 (iPhone)

1. Safari에서 `http://<서버IP>:3000` 접속
2. 하단 공유 버튼 → **홈 화면에 추가**
3. 앱 아이콘으로 실행 — 풀스크린 모드로 동작

---

## 기술 스택

| 항목 | 사용 기술 |
|---|---|
| 프레임워크 | Next.js 16 (App Router) |
| 스타일링 | Tailwind CSS v4 |
| 아이콘 | Lucide React |
| 언어 | TypeScript |
| 배포 | Vercel (예정) |
| 데이터 | Mock → Supabase (예정) |
