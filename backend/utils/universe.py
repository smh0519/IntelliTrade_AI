from datetime import date
from utils.logger import logger
from config import UNIVERSE_TICKERS

_cache: dict = {"tickers": None, "fetched_on": None}


def fetch_nasdaq100_universe() -> list[str]:
    """
    나스닥 100 현재 구성 종목 반환.
    우선순위: pytickersymbols (주간 갱신) → Wikipedia → config.py 하드코딩
    당일 캐시 적용 (하루 1회만 외부 조회).
    """
    today = date.today()
    if _cache["tickers"] and _cache["fetched_on"] == today:
        return _cache["tickers"]

    tickers = _try_pytickersymbols() or _try_wikipedia()

    if not tickers:
        logger.warning("[Universe] 모든 소스 실패 — config.py 하드코딩 목록으로 폴백")
        tickers = UNIVERSE_TICKERS[:]

    # 순서 유지하며 중복 제거
    seen = set()
    tickers = [t for t in tickers if not (t in seen or seen.add(t))]

    _cache["tickers"] = tickers
    _cache["fetched_on"] = today
    return tickers


def _try_pytickersymbols() -> list[str] | None:
    """pytickersymbols 패키지로 나스닥 100 Yahoo Finance 티커 조회."""
    try:
        from pytickersymbols import PyTickerSymbols
        tickers = list(PyTickerSymbols().get_nasdaq_100_nyc_yahoo_tickers())
        if len(tickers) >= 90:
            logger.info(f"[Universe] pytickersymbols: 나스닥 100 {len(tickers)}개 종목 로드 완료")
            return tickers
        logger.warning(f"[Universe] pytickersymbols 종목 수 이상 ({len(tickers)}개), 다음 소스 시도")
    except Exception as e:
        logger.warning(f"[Universe] pytickersymbols 실패: {e}")
    return None


def _try_wikipedia() -> list[str] | None:
    """Wikipedia 나스닥 100 구성 종목 테이블 스크래핑."""
    try:
        import pandas as pd
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100",
            attrs={"id": "constituents"},
        )
        df = tables[0]
        col = next((c for c in df.columns if c in ("Ticker", "Symbol")), None)
        if not col:
            raise ValueError(f"티커 컬럼 없음 — 실제 컬럼: {list(df.columns)}")
        tickers = [t.strip() for t in df[col].tolist() if isinstance(t, str) and t.strip()]
        if len(tickers) >= 90:
            logger.info(f"[Universe] Wikipedia: 나스닥 100 {len(tickers)}개 종목 로드 완료")
            return tickers
        raise ValueError(f"종목 수 이상: {len(tickers)}개")
    except Exception as e:
        logger.warning(f"[Universe] Wikipedia 실패: {e}")
    return None
