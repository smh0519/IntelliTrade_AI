import pandas as pd
import ta
import numpy as np
from utils.logger import logger

def calculate_breakout_target(df: pd.DataFrame, k: float = 0.5):
    """
    전략 A & B: 래리 윌리엄스 변동성 돌파 매매 타겟 라인 계산
    어제의 고가와 저가의 변동폭을 구한 뒤, 오늘 시초가에 더해 목표가를 산출합니다.
    (가장 마지막 행이 '오늘(진행 중)', 그 앞 행이 '어제'라고 가정)
    """
    if len(df) < 2:
        return None
        
    yesterday = df.iloc[-2]
    today_open = df.iloc[-1]['Open']
    
    range_val = yesterday['High'] - yesterday['Low']
    target_price = today_open + (range_val * k)
    
    return target_price

def check_volume_spike(df: pd.DataFrame, multiplier: float = 2.0):
    """
    전략 B 필터: 어제 거래량이 과거 20일 평균 거래량의 N배 이상 터졌는지 확인합니다.
    """
    if len(df) < 22:
        return False
        
    # 과거 20일 평균 거래량 (어제 제외, 그 이전 20일)
    past_20d_avg_vol = df['Volume'].iloc[-22:-2].mean()
    yesterday_vol = df['Volume'].iloc[-2]
    
    return yesterday_vol >= (past_20d_avg_vol * multiplier)

def calculate_ma_condition(df: pd.DataFrame, window: int = 20):
    """
    전략 B 필터: 현재 이동평균선이 상승 추세인지 판별합니다.
    """
    if len(df) < window + 1:
        return False
        
    ma_series = ta.trend.sma_indicator(df['Close'], window=window)
    current_ma = ma_series.iloc[-1]
    yesterday_ma = ma_series.iloc[-2]
    
    # 어제보다 오늘 MA 값이 높으면 상승 추세
    return current_ma > yesterday_ma

def check_bollinger_rsi_condition(df: pd.DataFrame, ma_window: int=20, std: int=2, rsi_window: int=14, rsi_threshold: int=30):
    """
    전략 C: 볼린저 밴드 하단 터치 및 RSI 과매도(30 이하) 동시 충족 여부
    """
    if len(df) < max(ma_window, rsi_window):
        return False
        
    # 볼린저 밴드 하단선 계산
    bb_lower = ta.volatility.bollinger_lband(df['Close'], window=ma_window, window_dev=std)
    # RSI 계산
    rsi = ta.momentum.rsi(df['Close'], window=rsi_window)
    
    current_price = df['Close'].iloc[-1]
    current_bb_lower = bb_lower.iloc[-1]
    current_rsi = rsi.iloc[-1]
    
    # 로그 기록용
    logger.debug(f"[C_Indicators] Price: {current_price:.2f}, BB_Lower: {current_bb_lower:.2f}, RSI: {current_rsi:.2f}")
    
    is_bb_touched = current_price <= current_bb_lower
    is_rsi_oversold = current_rsi <= rsi_threshold
    
    return is_bb_touched and is_rsi_oversold

def is_macro_trend_bullish(benchmark_df: pd.DataFrame, window: int = 200):
    """
    전략 C 필터: S&P500의 200일 이동평균선이 현재가보다 아래 있는지(대세 상승장인지) 확인합니다.
    """
    if benchmark_df is None or len(benchmark_df) < window:
        # 데이터가 충분하지 않다면 보수적으로 False 반환하거나, 일단 봇의 실행을 막지 않으려면 True
        return True 

    sp500_ma200 = ta.trend.sma_indicator(benchmark_df['Close'], window=window)
    current_close = benchmark_df['Close'].iloc[-1]
    current_ma200 = sp500_ma200.iloc[-1]
    
    logger.debug(f"[MacroFilter] S&P500 Close: {current_close:.2f}, 200MA: {current_ma200:.2f}")
    return current_close > current_ma200
