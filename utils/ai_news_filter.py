import os
import yfinance as yf
import anthropic
from utils.logger import logger
from dotenv import load_dotenv

load_dotenv()

# API 키 및 클라이언트 초기화 (에러 방어 포함)
api_key = os.getenv("ANTHROPIC_API_KEY")
client = None
if api_key:
    try:
        client = anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        logger.error(f"[AI News] Claude 클라이언트 초기화 실패: {e}")
else:
    logger.warning("[AI News] ANTHROPIC_API_KEY가 없습니다. AI 뉴스 마크맨 기능이 비활성화됩니다.")

def analyze_stock_news(symbol: str) -> bool:
    """
    지정된 종목의 최근 뉴스를 수집하고 Claude에게 판별을 맡깁니다.
    반환값: True(치명적 악재 있음 - 거래 중단 요망), False(안전함)
    """
    if not client:
        return False # API 키가 없으면 기본적으로 안전하다고 치부하고 매매 진행

    try:
        ticker = yf.Ticker(symbol)
        news_items = ticker.news

        if not news_items:
            logger.info(f"[{symbol}] 최근 분석할 뉴스가 없습니다.")
            return False

        # 최신 뉴스 5개의 제목을 파싱합니다.
        headlines = []
        for item in news_items[:5]:
            title = item.get("title", "")
            publisher = item.get("publisher", "")
            if title:
                headlines.append(f"- [{publisher}] {title}")

        news_text = "\n".join(headlines)
        logger.debug(f"[AI News] 수집된 {symbol} 헤드라인:\n{news_text}")

        # Claude 전용 프롬프트
        system_prompt = "당신은 월스트리트 헤지펀드의 최고 리스크 관리자입니다. 주식 뉴스를 분석하여 치명적 악재 여부만 간결하게 판단합니다."

        user_prompt = f"""이번 종목은 {symbol} 입니다.
다음은 방금 입수된 이 종목에 대한 최신 뉴스 헤드라인 5개입니다.

[뉴스 헤드라인]
{news_text}

이 뉴스들 중에서 당장 오늘 주가를 나락으로 떨어뜨릴 만한 극단적인 타격의 치명적 악재(Catastrophic risk)
예: 회계 부정, 파산 임박, CEO 구속, 핵심 파트너와의 초대형 계약 파기, 전례 없는 소송 패소 등이 있는지 판단하세요.
단순한 주가 하락전망, 애널리스트의 '보유' 의견 하향 등은 치명적 악재가 아닙니다.

명령:
평가 결과 최악의 치명적 악재가 있다면 오직 '[DANGER]' 라고만 답하세요.
그렇지 않고 버틸 수 있는 이슈거나 안전하다면 오직 '[SAFE]' 라고만 답하세요.
다른 부가 설명은 절대 하지 마세요."""

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=16,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        answer = response.content[0].text.strip().upper()

        if "[DANGER]" in answer:
            logger.critical(f"🚨 [AI News Marksman] {symbol}에 대한 치명적 악재가 감지되었습니다!")
            return True # 위험(Danger)
        else:
            logger.info(f"✅ [AI News Marksman] {symbol} 뉴스를 검사한 결과 치명적 악재는 없습니다 (SAFE).")
            return False # 안전(Safe)

    except Exception as e:
        logger.error(f"[AI News] 뉴스 분석 중 시스템 오류: {e}")
        return False # 에러 시 보수적으로 패스
