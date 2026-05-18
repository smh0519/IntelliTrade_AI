from datetime import date
import yfinance as yf
from utils.logger import logger


def fetch_earnings_dates(tickers: list[str]) -> dict[str, str | None]:
    """yfinance로 각 티커의 다음 실적 발표일을 조회합니다."""
    results: dict[str, str | None] = {}
    today = date.today()

    for ticker in tickers:
        try:
            cal = yf.Ticker(ticker).calendar
            if not isinstance(cal, dict):
                results[ticker] = None
                continue

            dates = cal.get("Earnings Date", [])
            if not isinstance(dates, list):
                dates = [dates]

            next_date = next(
                (d for d in dates if isinstance(d, date) and d >= today),
                None,
            )
            results[ticker] = str(next_date) if next_date else None
        except Exception as e:
            logger.warning(f"[Earnings] {ticker} 실적일 조회 실패: {e}")
            results[ticker] = None

    return results
