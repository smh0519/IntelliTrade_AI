import yfinance as yf
import pandas as pd
import ta
from utils.logger import logger

def run_daily_screener(tickers, top_n=5):
    """
    주어진 유니버스 목록을 스캔하여 오늘 집중 감시할 최적의 종목 TOP N개를 뽑아냅니다.
    """
    logger.info(f"🔎 [Screener] 프리마켓 종목 스캔 시작... (총 {len(tickers)}개 우량주 대상)")
    try:
        # 야후 파이낸스 다중 종목 배치 다운로드 (속도 빠름, IP 차단 회피)
        # 60일치 일봉 데이터를 한 번의 연결로 모두 가져옵니다.
        data = yf.download(tickers, period="60d", group_by="ticker", auto_adjust=True, progress=False)
        
        candidates = []
        for ticker in tickers:
            # yfinance 다중 티커 DataFrame 구조 처리
            if len(tickers) == 1:
                df = data
            else:
                if ticker not in data.columns.levels[0]:
                    continue
                df = data[ticker].copy()
                
            df = df.dropna()
            if len(df) < 20: 
                continue
            
            # 1. RSI 계산 (최근 14일)
            rsi_series = ta.momentum.rsi(df['Close'], window=14)
            current_rsi = rsi_series.iloc[-1]
            
            # 2. 변동성 계산 ((고가-저가)/종가 의 최근 5일 평균)
            volatility = (df['High'] - df['Low']) / df['Close']
            recent_vol = volatility.tail(5).mean()
            
            # 3. 이동평균 추세 확인 (20일선 위에 있는가?)
            ma20 = ta.trend.sma_indicator(df['Close'], window=20)
            is_uptrend = df['Close'].iloc[-1] > ma20.iloc[-1]
            
            candidates.append({
                "ticker": ticker,
                "rsi": current_rsi,
                "volatility": recent_vol,
                "is_uptrend": is_uptrend
            })
            
        if not candidates:
            logger.error("❌ [Screener] 스캔 결과 유효한 데이터가 없습니다.")
            return tickers[:top_n]
            
        # 1. 과매도 타겟 (RSI가 가장 낮은 종목 2개) - STRAT_C 타겟용
        sorted_by_rsi = sorted(candidates, key=lambda x: x['rsi'])
        top_oversold = [c['ticker'] for c in sorted_by_rsi[:2]]
        
        # 2. 돌파/추세 타겟 (상승장 20일선 위에 있으면서 최근 변동성이 가장 큰 종목 3개) - STRAT_A/B 타겟용
        uptrend_candidates = [c for c in candidates if c['is_uptrend'] and c['ticker'] not in top_oversold]
        sorted_by_vol = sorted(uptrend_candidates, key=lambda x: x['volatility'], reverse=True)
        top_volatility = [c['ticker'] for c in sorted_by_vol[:max(0, top_n - len(top_oversold))]]
        
        final_top = list(set(top_oversold + top_volatility))
        
        # 혹시라도 부족하면 (하락장이라 20일선 위 종목이 없는 등) 변동성 순으로 마저 채움
        if len(final_top) < top_n:
            remains = [c['ticker'] for c in sorted_by_vol if c['ticker'] not in final_top]
            final_top.extend(remains[:(top_n - len(final_top))])
            
        # 여전히 부족하면 원래 리스트로 땜빵
        if len(final_top) < top_n:
            for t in tickers:
                if t not in final_top and len(final_top) < top_n:
                    final_top.append(t)
                    
        logger.info(f"✨ [Screener] 🎯 오늘의 사냥감 TOP {len(final_top)} 선정 완료: {final_top}")
        return final_top
        
    except Exception as e:
        logger.error(f"❌ [Screener] 스크리너 핵심 오류 발생: {e}")
        return tickers[:top_n]
