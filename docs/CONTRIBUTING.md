# 협업 가이드

---

## 브랜치 전략

```
main              ← 최종 안정본 (직접 push 금지)
│
├── dev           ← 통합 테스트 (A + B 합치는 곳)
├── feature/strategy  ← A파트 작업 전용
└── feature/security  ← B파트 작업 전용
```

- `main`은 PR을 통해서만 머지
- `dev`는 항상 실행 가능한 상태 유지
- 작업 시작 전 항상 최신 `dev` pull 후 시작

```bash
git checkout feature/strategy   # 또는 feature/security
git pull origin dev
```

---

## 역할 분담

| 파트 | 담당 영역 | 주요 파일 |
|------|-----------|-----------|
| **A파트** | 트레이딩 전략·종목 분석 | `quant_logic.py`, `screener.py`, `universe.py`, `indicators.py`, `config.py` |
| **B파트** | 보안·안전벨트 구현 | `ai_news_filter.py`, `mock_account.py`, `withdrawal.py`, `telegram_bot.py`, `broker_api_client.py` |

상대방 담당 파일 수정 시 반드시 사전 협의.

---

## 공동 관리 파일

수정 전 상대방과 협의 필요:

| 파일 | 이유 |
|------|------|
| `config.py` | 전략 + 보안 파라미터 공유 |
| `quant_logic.py` | A파트 전략 + B파트 예외처리 혼재 |
| `rebalancer.py` | 매매 집행 핵심 로직 |
| `main.py` | 스케줄러·전체 흐름 제어 |
| `requirements.txt` | 패키지 추가 시 반드시 업데이트 |

---

## 커밋 메시지 규칙

```
타입: 한국어로 간단하게 설명
```

| 타입 | 사용 상황 |
|------|-----------|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 기능 변경 없이 코드 정리 |
| `docs` | 문서 수정 |
| `chore` | 설정·패키지 등 기타 |

```bash
# 좋은 예
feat: 출금 예약 기능 추가
fix: 소수점 매수 시 슬리피지 초과 오류 수정
refactor: universe 조회 캐시 로직 개선

# 나쁜 예
수정 / ㅇㅇ / fix
```

---

## PR 규칙

1. feature 브랜치 → `dev`로 PR 생성
2. 제목 형식: `[파트] 작업 내용 요약`
3. 본문: 무엇을 / 왜 / 테스트 여부
4. 상대방 리뷰 후 머지 (혼자 머지 금지)
5. 리뷰어 24시간 내 리뷰

---

## 코드 스타일

- 들여쓰기: 4칸 스페이스
- 함수명·변수명: `snake_case`
- 클래스명: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- 주석: 한국어

```python
# 권장 예외처리 패턴
try:
    result = some_api_call()
except Exception as e:
    logger.error(f"[모듈명] 오류 발생: {e}", exc_info=True)
```

---

## 보안 규칙

- `.env` 파일 커밋 금지
- API 키·토큰 코드 하드코딩 금지 — 환경변수로만 사용
- `mock_account.json` 실제 계좌 정보 포함 금지

---

## 로컬 환경 세팅

```bash
# 저장소 클론
git clone https://github.com/smh0519/IntelliTrade_AI.git
cd IntelliTrade_AI

# 백엔드 패키지 설치
cd backend
pip install -r requirements.txt

# .env 생성
IS_SIMULATION_MODE=true
ANTHROPIC_API_KEY=본인키
TELEGRAM_BOT_TOKEN=봇토큰
TELEGRAM_CHAT_ID=채팅숫자아이디
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...

# 실행 (반드시 시뮬레이션 모드로 먼저 테스트)
python main.py

# 프론트엔드
cd ../frontend
npm install
npm run dev
```
