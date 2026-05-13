import os
from datetime import datetime
from utils.logger import logger

try:
    from supabase import create_client, Client
    _SUPABASE_AVAILABLE = True
except ImportError:
    _SUPABASE_AVAILABLE = False

_client: "Client | None" = None


def _get_client() -> "Client | None":
    global _client
    if not _SUPABASE_AVAILABLE:
        return None
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return None

    _client = create_client(url, key)
    return _client


# ── 포트폴리오 스냅샷 ──────────────────────────────────────────────

def push_portfolio_snapshot(
    cash: float,
    total_value: float,
    initial_cash: float,
    pnl_pct: float,
    positions: dict,          # {ticker: {qty, avg_price, current_price}}
    current_prices: dict,     # {ticker: float}
):
    """포트폴리오 현황을 Supabase에 저장합니다."""
    client = _get_client()
    if not client:
        return

    enriched = {}
    for ticker, info in positions.items():
        enriched[ticker] = {
            "qty":           round(info.get("qty", 0), 6),
            "avg_price":     round(info.get("avg_price", 0), 4),
            "current_price": round(current_prices.get(ticker, info.get("avg_price", 0)), 4),
        }

    try:
        client.table("portfolio_snapshots").insert({
            "cash":         round(cash, 4),
            "total_value":  round(total_value, 4),
            "initial_cash": round(initial_cash, 4),
            "pnl_pct":      round(pnl_pct, 4),
            "positions":    enriched,
        }).execute()
        logger.info("☁️  [Supabase] 포트폴리오 스냅샷 저장 완료")
    except Exception as e:
        logger.error(f"[Supabase] 포트폴리오 저장 실패: {e}")


# ── 모멘텀 랭킹 ──────────────────────────────────────────────────────

def push_momentum_rankings(full_ranking: list, portfolio: list):
    """모멘텀 랭킹을 Supabase에 저장합니다."""
    client = _get_client()
    if not client:
        return

    rankings = [
        {
            "rank":         i + 1,
            "ticker":       ticker,
            "in_portfolio": ticker in portfolio,
        }
        for i, ticker in enumerate(full_ranking)
    ]

    try:
        client.table("momentum_rankings").insert({"rankings": rankings}).execute()
        logger.info("☁️  [Supabase] 모멘텀 랭킹 저장 완료")
    except Exception as e:
        logger.error(f"[Supabase] 랭킹 저장 실패: {e}")


# ── 거래 내역 ────────────────────────────────────────────────────────

def push_trade(
    action: str,
    ticker: str,
    qty: float,
    price: float,
    strategy_tag: str = "N10_MEW",
):
    """매수/매도 거래를 Supabase에 기록합니다."""
    client = _get_client()
    if not client:
        return

    try:
        client.table("trade_log").insert({
            "action":       action,
            "ticker":       ticker,
            "qty":          round(qty, 6),
            "price":        round(price, 4),
            "total_amount": round(qty * price, 4),
            "strategy_tag": strategy_tag,
        }).execute()
        logger.info(f"☁️  [Supabase] 거래 기록: {action.upper()} {ticker} {qty}주 @ ${price:.2f}")
    except Exception as e:
        logger.error(f"[Supabase] 거래 기록 실패: {e}")


# ── 리밸런싱 이력 ────────────────────────────────────────────────────

def push_rebalance_log(
    reason: str,
    new_portfolio: list,
    sold_tickers: list,
    bought_tickers: list,
):
    """리밸런싱 완료 이벤트를 Supabase에 기록합니다."""
    client = _get_client()
    if not client:
        return

    try:
        client.table("rebalance_log").insert({
            "reason":         reason,
            "new_portfolio":  new_portfolio,
            "sold_tickers":   sold_tickers,
            "bought_tickers": bought_tickers,
        }).execute()
        logger.info("☁️  [Supabase] 리밸런싱 이력 저장 완료")
    except Exception as e:
        logger.error(f"[Supabase] 리밸런싱 저장 실패: {e}")
