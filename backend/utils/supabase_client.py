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
    user_id: str = "",
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
        row = {
            "cash":         round(cash, 4),
            "total_value":  round(total_value, 4),
            "initial_cash": round(initial_cash, 4),
            "pnl_pct":      round(pnl_pct, 4),
            "positions":    enriched,
        }
        if user_id:
            row["user_id"] = user_id
        client.table("portfolio_snapshots").insert(row).execute()
        logger.info("☁️  [Supabase] 포트폴리오 스냅샷 저장 완료")
    except Exception as e:
        logger.error(f"[Supabase] 포트폴리오 저장 실패: {e}")


# ── 모멘텀 랭킹 ──────────────────────────────────────────────────────

def push_momentum_rankings(full_ranking: list, portfolio: list, user_id: str = ""):
    """모멘텀 랭킹을 Supabase에 저장합니다."""
    client = _get_client()
    if not client:
        return

    rankings = [
        {
            "rank":         i + 1,
            "ticker":       r["ticker"],
            "momentum_pct": r.get("momentum_pct", 0),
            "in_portfolio": r["ticker"] in portfolio,
        }
        for i, r in enumerate(full_ranking)
    ]

    try:
        row: dict = {"rankings": rankings}
        if user_id:
            row["user_id"] = user_id
        client.table("momentum_rankings").insert(row).execute()
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
    user_id: str = "",
):
    """매수/매도 거래를 Supabase에 기록합니다."""
    client = _get_client()
    if not client:
        return

    try:
        row = {
            "action":       action,
            "ticker":       ticker,
            "qty":          round(qty, 6),
            "price":        round(price, 4),
            "total_amount": round(qty * price, 4),
            "strategy_tag": strategy_tag,
        }
        if user_id:
            row["user_id"] = user_id
        client.table("trade_log").insert(row).execute()
        logger.info(f"☁️  [Supabase] 거래 기록: {action.upper()} {ticker} {qty}주 @ ${price:.2f}")
    except Exception as e:
        logger.error(f"[Supabase] 거래 기록 실패: {e}")


# ── 브로커 자격증명 ───────────────────────────────────────────────────

def load_broker_credentials(user_id: str) -> dict | None:
    """
    Supabase user_broker_credentials 테이블에서 해당 유저의 증권계좌 설정을 불러옵니다.
    반환값: {"api_key", "secret_key", "account_id", "base_url", "is_simulation_mode"}
    설정이 없으면 None 반환.
    """
    client = _get_client()
    if not client or not user_id:
        return None

    try:
        res = client.table("user_broker_credentials").select("*").eq("user_id", user_id).maybeSingle().execute()
        return res.data  # None이면 설정 없음
    except Exception as e:
        logger.error(f"[Supabase] 브로커 자격증명 로드 실패: {e}")
        return None


# ── 실적 캘린더 ──────────────────────────────────────────────────────

def push_earnings_calendar(earnings: dict):
    """
    {ticker: 'YYYY-MM-DD' or None} 형태를 earnings_calendar 테이블에 upsert합니다.
    """
    client = _get_client()
    if not client:
        return

    rows = [
        {"ticker": ticker, "earnings_date": date_str, "updated_at": datetime.utcnow().isoformat()}
        for ticker, date_str in earnings.items()
    ]
    if not rows:
        return

    try:
        client.table("earnings_calendar").upsert(rows, on_conflict="ticker").execute()
        logger.info(f"☁️  [Supabase] 실적 캘린더 저장 완료 ({len(rows)}개)")
    except Exception as e:
        logger.error(f"[Supabase] 실적 캘린더 저장 실패: {e}")


# ── 리밸런싱 이력 ────────────────────────────────────────────────────

def push_rebalance_log(
    reason: str,
    new_portfolio: list,
    sold_tickers: list,
    bought_tickers: list,
    user_id: str = "",
):
    """리밸런싱 완료 이벤트를 Supabase에 기록합니다."""
    client = _get_client()
    if not client:
        return

    try:
        row = {
            "reason":         reason,
            "new_portfolio":  new_portfolio,
            "sold_tickers":   sold_tickers,
            "bought_tickers": bought_tickers,
        }
        if user_id:
            row["user_id"] = user_id
        client.table("rebalance_log").insert(row).execute()
        logger.info("☁️  [Supabase] 리밸런싱 이력 저장 완료")
    except Exception as e:
        logger.error(f"[Supabase] 리밸런싱 저장 실패: {e}")
