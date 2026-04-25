# 🤝 IntelliTrade AI — 협업 가이드 (CONTRIBUTING.md)

> 이 문서는 2인 개발 협업 시 지켜야 할 브랜치 전략, 커밋 규칙, 코드 스타일을 정의합니다.  
> 작업 시작 전 반드시 읽고 숙지해주세요.

---

## 👥 역할 분담

| 파트 | 담당 영역 | 주요 파일 |
|------|-----------|-----------|
| **A파트** | 트레이딩 전략 및 종목 분석 | `quant_logic.py`, `utils/screener.py`, `utils/indicators.py`, `utils/market_data.py`, `config.py` |
| **B파트** | 보안 및 안전벨트 구현 | `utils/ai_news_filter.py`, `utils/mock_account.py`, `utils/telegram_bot.py`, `utils/notifier.py`, `utils/broker_api_client.py` |

> ⚠️ 상대방 담당 파일을 수정해야 할 경우, 반드시 사전에 협의 후 진행합니다.

---

## 🌿 브랜치 전략

### 브랜치 구조

```
main                  ← 최종 안정본 (직접 push 절대 금지)
│
├── dev               ← 통합 테스트 브랜치 (A + B 합치는 곳)
│
├── feature/strategy  ← A파트 작업 전용
│
└── feature/security  ← B파트 작업 전용
```

### 흐름

```
각자 feature 브랜치에서 작업
    → dev로 PR 올리기
    → 상대방 코드리뷰 후 머지
    → 충분히 테스트된 것만 main으로 머지
```

### 규칙

- `main`에 직접 push 금지 — PR을 통해서만 머지
- `dev`는 항상 실행 가능한 상태 유지
- 각자 본인 feature 브랜치에서만 작업
- 작업 시작 전 항상 최신 `dev`를 pull 받고 시작

```bash
# 작업 시작 전 항상 실행
git checkout feature/security   # 또는 feature/strategy
git pull origin dev
```

---

## 💬 커밋 메시지 규칙

### 형식

```
타입: 한국어로 간단하게 설명
```

### 타입 종류

| 타입 | 사용 상황 | 예시 |
|------|-----------|------|
| `feat` | 새 기능 추가 | `feat: 일일 최대 손실 한도 차단 로직 추가` |
| `fix` | 버그 수정 | `fix: 텔레그램 알림 재전송 실패 오류 수정` |
| `refactor` | 기능 변경 없이 코드 정리 | `refactor: mock_account 저장 로직 원자적 처리로 개선` |
| `docs` | 문서 수정 | `docs: CONTRIBUTING.md 브랜치 설명 보완` |
| `chore` | 설정, 패키지 등 기타 작업 | `chore: .gitignore에 .env 추가 확인` |
| `test` | 테스트 코드 추가/수정 | `test: ai_news_filter 악재 판별 단위 테스트 추가` |

### 좋은 예 / 나쁜 예

```bash
# ✅ 좋은 예
feat: 봇 비정상 종료 시 텔레그램 긴급 알림 발송 기능 추가
fix: 가상 계좌 잔고 음수 방지 검증 누락 수정
refactor: check_exit_conditions 함수 가독성 개선

# ❌ 나쁜 예
수정
ㅇㅇ
aaa
fix
```

---

## 🔀 PR (Pull Request) 규칙

### PR 올리는 방법

1. 본인 feature 브랜치 → `dev`로 PR 생성
2. PR 제목 형식: `[파트] 작업 내용 요약`
   ```
   [B파트] 가상 계좌 무결성 보호 로직 추가
   [A파트] STRAT_B 거래량 조건 파라미터 튜닝
   ```
3. PR 본문에 아래 내용 포함:
   - 무엇을 했는지
   - 왜 했는지
   - 테스트 했는지 여부

### 코드리뷰 규칙

- PR 올린 후 상대방 리뷰 받고 머지 (혼자 머지 금지)
- 리뷰어는 24시간 내 리뷰
- 충돌(conflict) 발생 시 PR 올린 사람이 직접 해결 후 다시 요청

---

## 🐍 코드 스타일

### 기본 규칙

- 들여쓰기: **4칸 스페이스** (탭 사용 금지)
- 함수명/변수명: **snake_case** (`check_exit_conditions`, `current_price`)
- 클래스명: **PascalCase** (`TradingStrategy`, `BrokerAPIClient`)
- 상수: **UPPER_SNAKE_CASE** (`STRAT_A_TP`, `MIN_CASH_BALANCE`)

### 주석

- 주석은 **한국어**로 작성
- 함수에는 한 줄 이상 역할 설명 포함

```python
# ✅ 좋은 예
def check_exit_conditions(self, current_prices_dict):
    """실시간 수익률을 검사하여 TP/SL 조건 도달 시 즉시 청산합니다."""
    pass

# ❌ 나쁜 예
def f(d):
    pass
```

### 예외처리

- B파트 담당 모든 함수에는 `try/except` 필수
- 예외 발생 시 `logger`로 기록 + 텔레그램 알림 고려

```python
# ✅ 권장 패턴
try:
    result = some_api_call()
except Exception as e:
    logger.error(f"[모듈명] 오류 발생: {e}", exc_info=True)
```

---

## 🔐 보안 규칙

- `.env` 파일은 절대 커밋 금지 (`.gitignore` 확인 필수)
- API 키, 텔레그램 토큰은 코드에 하드코딩 금지 — 반드시 환경변수로만 사용
- `mock_account.json` 실제 계좌 정보 포함 금지

```bash
# .env에 있어야 할 것들
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
IS_SIMULATION_MODE=true
```

---

## ⚙️ 공동 관리 파일

아래 파일은 양쪽 모두 영향을 주므로 **수정 전 반드시 상대방과 협의**합니다.

| 파일 | 이유 |
|------|------|
| `config.py` | TP/SL, 타임컷 등 전략 + 보안 파라미터 공유 |
| `quant_logic.py` | A파트 전략 + B파트 예외처리가 혼재 |
| `main.py` | 스케줄러 설정, 전체 흐름 제어 |
| `requirements.txt` | 패키지 추가 시 반드시 업데이트 |

---

## 🚀 로컬 환경 세팅

```bash
# 1. 저장소 클론
git clone https://github.com/smh0519/IntelliTrade_AI.git
cd IntelliTrade_AI

# 2. 패키지 설치
pip install requests python-dotenv schedule pandas numpy ta yfinance anthropic pykrx pytz rich

# 3. .env 파일 생성 (직접 작성)
cp .env.example .env   # .env.example이 있는 경우
# 없으면 직접 아래 내용으로 생성:
# IS_SIMULATION_MODE=true
# ANTHROPIC_API_KEY=본인키
# TELEGRAM_BOT_TOKEN=봇토큰
# TELEGRAM_CHAT_ID=채팅숫자아이디

# 4. 실행 (반드시 시뮬레이션 모드로 먼저 테스트)
python main.py
```

---

## ❓ 협업 중 문제 생기면

- 코드 충돌 → 본인이 해결 후 PR 재요청
- 담당 파일 경계 애매한 경우 → 먼저 상의
- 긴급 버그 발견 시 → `fix/버그명` 브랜치 따서 빠르게 처리 후 dev로 PR