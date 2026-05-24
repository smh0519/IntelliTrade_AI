# IntelliTrade AI — N10-MEW

나스닥 100 모멘텀 동일가중(N10-MEW) 전략 기반 자동 매매 시스템.

Python 백엔드 봇 + Next.js 모바일 대시보드로 구성됩니다.

---

## 전략 요약

| 항목 | 내용 |
|------|------|
| 유니버스 | 나스닥 100 현재 구성 종목 (pytickersymbols 주간 자동 갱신) |
| 선정 신호 | 최근 3개월(63영업일) 수익률 상위 10개 |
| 자산 배분 | 동일비중 10% |
| 리밸런싱 | 매월 첫 영업일 09:30 AM (뉴욕, 정규장 개장 즉시) |
| 즉시 교체 | 보유 종목이 12위 밖으로 이탈 시 자동 교체 |

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

## 현재 진행상황

### 백엔드

- [x] N10-MEW 전략 루프 (`main.py` + `quant_logic.py`) 구현 완료
- [x] 나스닥 100 유니버스 동적 조회 (`utils/universe.py`) 구현 완료
  - pytickersymbols → Wikipedia → config.py 폴백 3단계
- [x] 월간/이탈 기반 리밸런싱 엔진 (`rebalancer.py`) 구현 완료
  - 3단계 파이프라인: 탈락 매도 → 과비중 조정 → 소수점 매수
  - 집행 시각 09:30 AM (뉴욕) 적용
- [x] 소수점 매매 및 슬리피지 선반영 (`usable_cash = available_cash / 1.0005`)
- [x] 출금 예약 기능 (`utils/withdrawal.py`) 구현 완료
  - 리밸런싱 전 예약액 차감 → 리밸런싱 후 자동 초기화
- [x] 모의투자 장부 (`data/mock_account.json`) 기반 페이퍼 트레이딩 동작
- [x] 텔레그램 알림 및 명령 제어 연동 완료
- [x] Supabase 적재 파이프라인 구성 완료
- [x] 백테스트 스크립트 (`backtest.py`) 포함
- [ ] 실거래 브로커 API 연동 (추가 작업 예정)

### 프론트엔드

- [x] 모바일 대시보드 PWA (5탭) 구현 완료
  - 개요 / 보유종목 / 모멘텀 / 리밸런싱 / 뉴스
- [x] 이중 갱신 인터벌 적용
  - 5분: 현재가·수익률·평가액 (`/api/prices`)
  - 15분: 전체 데이터 (`/api/dashboard`)
- [x] 출금 예약 카드 + 모달 UI 구현 완료
- [x] 실적 발표 D-day 알림 카드
- [x] 뉴스 탭: 네이버 뉴스 기반 한국어 뉴스 피드 + 앱 내 기사 본문
- [x] QQQ·SPY·DIA 벤치마크 수익률 비교
- [ ] 실거래 연동 시 실시간 데이터 반영 확인 필요
