import yfinance as yf
import pandas as pd
from utils.logger import logger

def fetch_historical_data(symbol: str, period: str = "60d", interval: str = "1d") -> pd.DataFrame:
    """
    주어진 종목의 과거 데이터를 가져옵니다.
    """
    try:
        logger.debug(f"[MarketData] {symbol} 데이터 다운로드 중... (기간: {period}, 간격: {interval})")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            logger.error(f"[MarketData] {symbol} 데이터를 받아오지 못했습니다.")
            return None
            
        return df
    except Exception as e:
        logger.error(f"[MarketData] 데이터 페치 중 에러 발생 ({symbol}): {e}")
        return None

def fetch_benchmark_data(symbol: str = "SPY", period: str = "250d", interval: str = "1d") -> pd.DataFrame:
    """
    시장 매크로 필터(S&P 500 등) 용 벤치마크 데이터를 가져옵니다.
    """
    return fetch_historical_data(symbol, period=period, interval=interval)
