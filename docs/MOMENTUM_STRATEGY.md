# N10-MEW 전략 — 현재 구현 상태

## 1. 유니버스 선정

`utils/universe.py`의 `fetch_nasdaq100_universe()`가 나스닥 100 현재 구성 종목을 동적으로 조회한다.

**조회 우선순위**

| 순위 | 소스 | 갱신 주기 | 비고 |
|------|------|-----------|------|
| 1 | `pytickersymbols` | 주 1회 (GitHub Actions) | Yahoo Finance 형식 티커 반환 |
| 2 | Wikipedia 스크래핑 | 실시간 | `#constituents` 테이블 파싱 |
| 3 | `config.py` 하드코딩 | 수동 업데이트 | 50개 고정 목록 (최종 폴백) |

- 당일 캐시 적용 — 봇이 1시간마다 실행되어도 하루 1회만 외부 요청
- 중복 티커 자동 제거 (GOOGL/GOOG 등 이중 상장 종목 처리)

---

## 2. 모멘텀 계산

`utils/screener.py`의 `run_momentum_screener()`에서 유니버스 전 종목의 3개월 모멘텀을 계산한다.

```
momentum = (price_now / price_past) - 1.0

price_now  = 오늘 종가
price_past = 63영업일 전 종가 (≈ 3개월)
```

- yfinance로 78일치 일봉 데이터 배치 다운로드 (63일 + 공휴일 버퍼 15일)
- 단순 가격 수익률만 사용 (거래량·변동성·EPS 미반영)
- 결과: `[{"ticker": str, "momentum_pct": float}, ...]` 내림차순

---

## 3. 종목 선정 및 포트폴리오 구성

| 항목 | 값 | 파라미터 |
|------|-----|---------|
| 편입 종목 수 | 상위 10개 | `TOP_N_PORTFOLIO = 10` |
| 관찰 버퍼 | 11~12위 | `REBALANCE_EXIT_RANK = 12` |
| 즉시 교체 기준 | 12위 밖 이탈 | `REBALANCE_EXIT_RANK = 12` |
| 비중 방식 | 동일비중 10% | `WEIGHT_PER_STOCK = 0.10` |
| 비중 조정 임계값 | ±2% 이내 조정 없음 | `REBALANCE_THRESHOLD = 0.02` |
| 모멘텀 기간 | 63영업일 (≈ 3개월) | `MOMENTUM_PERIOD_DAYS = 63` |

`execute_strategy()`에서 상위 14개를 스크리너에 요청 (`REBALANCE_EXIT_RANK + 2 = 14`).  
포트폴리오 10개 + 이탈 감지 버퍼 4개.

---

## 4. 리밸런싱 트리거

`rebalancer.py`의 `N10MEWRebalancer`가 아래 3가지 조건을 순서대로 확인한다.

### 트리거 1 — 초기 포트폴리오 구성

```
보유 종목 없음 AND 현재 포트폴리오 없음
  → execute_rebalance(force=True) 즉시 실행
  → 집행 시간 제한 없음
```

### 트리거 2 — 월간 정기 리밸런싱

```
오늘 == 해당 월의 첫 영업일
AND 이번 달 아직 리밸런싱 미실행 (last_rebalance_month != 이번 달)
AND 현재 시각 >= 09:30 AM (뉴욕 기준)
  → execute_rebalance() 실행
```

- 첫 영업일 판별: 1일이 토요일이면 3일(월), 일요일이면 2일(월)로 자동 보정
- `REBALANCE_EXECUTION_TIME = "09:30"` — 정규장 개장과 동시에 집행

### 트리거 3 — 랭킹 이탈 즉시 교체

```
현재 포트폴리오 종목 중 하나라도
  모멘텀 랭킹 12위 밖으로 이탈
    → execute_rebalance() 즉시 실행
```

- `check_rank_drift()`: 보유 종목 ∩ 현재 Top 12 비교
- 이탈 종목명과 이유를 로그에 기록

---

## 5. 리밸런싱 집행 — 3단계 파이프라인

`execute_rebalance()` 내부 실행 순서:

### 5-1. 출금 예약 확인

```
withdrawal.get_reservation() → 예약액 조회
investable = total_value - withdrawal_amount
target_per_stock = investable × WEIGHT_PER_STOCK
```

- 예약액이 총 자산 이상이면 무시
- 리밸런싱 완료 후 `withdrawal.clear_reservation()` 자동 초기화

### 5-2. 1단계 — 탈락 종목 전량 매도

```
for ticker in 현재 보유 종목:
    if ticker not in new_top10:
        전량 매도 → 현금 확보
```

### 5-3. 2단계 — 과비중 종목 조정 매도

```
for ticker in new_top10 ∩ 보유 종목:
    drift = (현재가치 - target_per_stock) / target_per_stock
    if drift > REBALANCE_THRESHOLD (2%):
        초과분만큼 매도
```

### 5-4. 3단계 — 신규 편입 및 과소비중 매수

```
for ticker in new_top10:
    drift = (target_per_stock - 현재가치) / target_per_stock
    if drift > REBALANCE_THRESHOLD (2%):
        usable_cash = available_cash / 1.0005  ← 슬리피지 0.05% 선반영
        buy_value = min(부족분, usable_cash)
        buy_qty = round(buy_value / current_price, 4)  ← 소수점 매매
        매수 실행
```

- `buy_qty`는 소수점 4자리까지 허용 (소수점 매매)
- 가용 현금을 슬리피지로 나눠 실제 체결 가능 금액 산출
- 가용 현금이 없으면 해당 종목 매수 건너뜀

---

## 6. 가상 장부 (시뮬레이션 모드)

`IS_SIMULATION_MODE=true` 시 `data/mock_account.json`에 장부를 보관한다.

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

- `execute_virtual_buy` / `execute_virtual_sell`: 체결 시 슬리피지 0.05% 자동 적용
- 평단가 가중평균 자동 계산
- 포지션을 전략 태그(`N10_MEW`) 단위로 구분 → 멀티 전략 확장 가능

---

## 7. 리스크 관리

| 항목 | 조건 | 동작 |
|------|------|------|
| 포트폴리오 전체 손실 경고 | 수익률 ≤ -20% | 텔레그램 긴급 알림 |
| 랭킹 이탈 즉시 교체 | 보유 종목 12위 밖 이탈 | 즉시 리밸런싱 실행 |
| 비중 조정 임계값 | 오차 < 2% | 거래 생략 (수수료 절감) |
| 주문 타임아웃 | 5분 미체결 | 주문 자동 취소 |

---

## 8. Supabase 적재

리밸런싱 및 전략 실행 결과는 `utils/supabase_client.py`를 통해 Supabase에 저장된다.

| 테이블 | 저장 시점 | 주요 데이터 |
|--------|----------|-------------|
| `portfolio_snapshots` | 매 1시간 | 현금, 총 자산, 포지션별 수량·평단가·현재가 |
| `momentum_rankings` | 매 1시간 | Top 14 종목, 모멘텀 수익률, 편입 여부 |
| `rebalance_log` | 리밸런싱 시 | 사유, 매도 종목, 매수 종목, 날짜 |
| `trade_log` | 개별 체결 시 | 종목, 방향, 수량, 체결가 |
| `earnings_calendar` | 매 1시간 | 보유 종목 실적 발표 예정일 |

---

*최종 업데이트: 2026-05-24*
