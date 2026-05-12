import yfinance as yf
from utils.logger import logger
from config import MOMENTUM_PERIOD_DAYS


def run_momentum_screener(tickers: list, top_n: int = 12) -> list:
    """
    유니버스 전 종목의 3개월 모멘텀을 계산하여 상위 top_n개를 반환합니다.

    - 모멘텀 = (현재가 / MOMENTUM_PERIOD_DAYS일 전 가격) - 1
    - 순수 수익률 기준으로 정렬하며 테마 보정 없음
    - top_n 기본값 12: 포트폴리오 10개 + 이탈 감지 버퍼 2개
    """
    logger.info(
        f"🔎 [Screener] N10-MEW 모멘텀 스캔 시작 "
        f"(유니버스 {len(tickers)}개, 기간 {MOMENTUM_PERIOD_DAYS}일)"
    )

    download_days = MOMENTUM_PERIOD_DAYS + 15  # 공휴일 등 버퍼 포함
    try:
        raw = yf.download(
            tickers,
            period=f"{download_days}d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
        )
    except Exception as e:
        logger.error(f"❌ [Screener] 데이터 다운로드 실패: {e}")
        return tickers[:top_n]

    candidates = []
    for ticker in tickers:
        try:
            df = (raw[ticker] if len(tickers) > 1 else raw).dropna()
        except (KeyError, AttributeError):
            logger.warning(f"⚠️ [Screener] {ticker} 데이터 없음, 건너뜁니다.")
            continue

        if len(df) < MOMENTUM_PERIOD_DAYS:
            logger.warning(
                f"⚠️ [Screener] {ticker} 데이터 부족 ({len(df)}행), 건너뜁니다."
            )
            continue

        price_now = float(df["Close"].iloc[-1])
        price_past = float(df["Close"].iloc[-MOMENTUM_PERIOD_DAYS])

        if price_past <= 0:
            continue

        momentum = (price_now / price_past) - 1.0
        candidates.append({"ticker": ticker, "momentum": momentum})

    if not candidates:
        logger.error("❌ [Screener] 유효한 종목이 없습니다. 원본 유니버스 상위를 반환합니다.")
        return tickers[:top_n]

    candidates.sort(key=lambda x: x["momentum"], reverse=True)

    result = [c["ticker"] for c in candidates[:top_n]]
    logger.info(f"✨ [Screener] 모멘텀 Top {top_n} 선정: {result}")

    for c in candidates[:5]:
        logger.info(f"   {c['ticker']}: {c['momentum'] * 100:+.2f}% (3M 모멘텀)")

    return result
