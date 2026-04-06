# 퀀트 주식 자동 매매 시스템 (Quant Bot)

## 🚀 프로젝트 개요

이 프로젝트는 파이썬(Python)을 기반으로 운영되는 퀀트 주식 자동 매매 시스템입니다. `pandas`와 `numpy` 등 데이터 분석 라이브러리를 활용하여 주식 데이터를 가공하고, 설정된 기술적 지표(현재 이동평균선 전략 포함)에 따라 매수/매도 신호를 자동 생성합니다. 더불어 증권사 API 연동을 통해 자동화된 주문 실행을 목표로 하고 있습니다.

또한 Google Gemini API를 통합하여, 단순 룰 기반 자동 매매뿐 아니라 AI 기반 시장 분석 및 프로젝트 코드 개발을 즉각적으로 지원받을 수 있는 확장성 있는 구조를 갖추고 있습니다.

## 🛠️ 기술 스택 

- **언어**: Python 3
- **데이터 핸들링**: Pandas, Numpy
- **금융 데이터 소스**: PyKrx, Requests
- **인공지능(AI)**: Google Generative AI (Gemini 2.5 Flash)
- **기타 설정 관리**: Python-dotenv
- **UI (CLI)**: Rich (의존성 패키지)

## 📁 프로젝트 구조 및 주요 파일

```text
quant_bot/
├── main.py               # 프로그램 진입점 (자동 매매 루프 실행)
├── quant_logic.py        # 퀀트 분석 및 매매 판단 로직 (이동평균선 기반)
├── gemini_pro.py         # AI 퀀트/코딩 어시스턴트 CLI (코드 작성 및 파일 자동생성 지원)
├── config/               
│   └── settings.py       # 시뮬레이션 모드, 익절/손절 비율 등 설정 파일
├── utils/                
│   ├── api_handler.py    # 증권사 API 연동 및 시장 데이터 수집 유틸
│   └── notifier.py       # 애플리케이션 로그, 매매 결과 알림 (Discord/Slack 등 연동 예상)
├── README.md             # 프로젝트 개요 및 설명
├── requirements.txt      # 파이썬 의존성 패키지 목록
└── .env                  # API KEY 등 민감한 환경변수 설정 파일 (git 적용 제외 권장)
```

### 핵심 모듈 세부 설명
*   **`main.py`**: 초기 시스템이 구동되며 관종 리스트(`WATCHLIST`) 주식을 감시합니다. 무한루프를 돌며 정해진 주기마다 현재 자산 상태를 갱신하고 `quant_logic` 객체를 통해 매매를 결정합니다.
*   **`quant_logic.py (QuantStrategy)`**: 주가 과거 데이터를 조회해(MA20) 이동평균선을 비롯한 지표를 계산합니다. 설정된 `TARGET_PROFIT_RATE`, `STOP_LOSS_RATE`에 도달하면 이익/손절매를 트리거합니다.
*   **`gemini_pro.py`**: 개발 생산성을 높이기 위한 AI 챗봇입니다. 콘솔(CLI)에서 자연어 대화로 지시하면 퀀트 로직 파이썬 파일이나 리포트를 자동으로 프로젝트 폴더에 생성 및 저장해 줍니다. 

## ⚙️ 실행 방법 (Usage)

**(1) 필요 패키지 설치**
```bash
pip install -r requirements.txt
pip install rich # gemini_pro.py UI 전용
```

**(2) 환경 설정 (.env)**
프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 아래와 같이 필요한 키값을 세팅해야 합니다.
```env
GEMINI_API_KEY="본인의_제미나이_API_KEY 입력"
# 이 외에 증권사 API 설정 등
```

**(3) 스크립트 실행**
- **매매 봇 실행**:
```bash
python main.py
```
- **Gemini 코딩 어시스턴트(멘토) 실행**:
```bash
python gemini_pro.py
```

## 📝 향후 업데이트 예정(To-Do)

- [ ] `main.py`에 실제 시장 개장 시간에 맞춘 크론 무한루프 구동 추가
- [ ] 하드코딩된 관심 종목 리스트(`WATCHLIST`)를 DB 연동 또는 JSON 방식으로 동적으로 분리
- [ ] `quant_logic.py` 내 볼린저밴드, RSI, MACD 등 다양한 전략 추가
- [ ] Gemini API를 활용하여 포트폴리오 다각화 아이디어 도출 등 투자 핵심 의사 결정 자동화
