#!/usr/bin/env python3
"""
현재 mock_account.json 데이터를 Supabase 초기 스냅샷으로 업로드
실행: python seed_supabase.py
"""
import os, json, sys
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client
import yfinance as yf

client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
)

# mock_account.json 읽기
with open("data/mock_account.json") as f:
    account = json.load(f)

initial_cash = account["initial_cash"]
cash = account["cash"]
holdings = account["positions"].get("N10_MEW", {})

print(f"💰 현금: ${cash:.2f}  |  보유 종목: {len(holdings)}개")
print("📡 현재가 조회 중...")

tickers = list(holdings.keys())
prices = {}
if tickers:
    raw = yf.download(tickers, period="1d", progress=False, auto_adjust=True)
    for t in tickers:
        try:
            prices[t] = float(raw["Close"][t].dropna().iloc[-1])
        except Exception:
            prices[t] = holdings[t]["avg_price"]

# 포지션 + 총 자산 계산
total_value = cash
positions_out = {}
for ticker, info in holdings.items():
    cur_p = prices.get(ticker, info["avg_price"])
    total_value += info["qty"] * cur_p
    positions_out[ticker] = {
        "qty":           round(info["qty"], 6),
        "avg_price":     round(info["avg_price"], 4),
        "current_price": round(cur_p, 4),
    }

pnl_pct = ((total_value - initial_cash) / initial_cash) * 100
print(f"📊 총 자산: ${total_value:.2f}  |  수익률: {pnl_pct:+.2f}%")

# portfolio_snapshots 삽입
client.table("portfolio_snapshots").insert({
    "cash":         round(cash, 4),
    "total_value":  round(total_value, 4),
    "initial_cash": initial_cash,
    "pnl_pct":      round(pnl_pct, 4),
    "positions":    positions_out,
}).execute()
print("✅ portfolio_snapshots 저장 완료")

# trade_log — 기존 매수 내역 삽입
for ticker, info in holdings.items():
    client.table("trade_log").insert({
        "action":       "buy",
        "ticker":       ticker,
        "qty":          round(info["qty"], 6),
        "price":        round(info["avg_price"], 4),
        "total_amount": round(info["qty"] * info["avg_price"], 4),
        "strategy_tag": "N10_MEW",
    }).execute()
print(f"✅ trade_log {len(holdings)}건 저장 완료")

# rebalance_log — 초기 구성 기록
client.table("rebalance_log").insert({
    "reason":         "초기 포트폴리오 구성",
    "new_portfolio":  tickers,
    "sold_tickers":   [],
    "bought_tickers": tickers,
}).execute()
print("✅ rebalance_log 저장 완료")

print("\n🎉 초기 데이터 업로드 완료!")
