"""
GitHub Actions용 단일 실행 runner.
전략 1사이클을 실행하고 종료 (무한 루프 없음, Telegram 폴링 없음).

Usage:
    python run_once.py                  # 전략 실행 (날짜 조건 정상 적용)
    python run_once.py --news           # 뉴스 악재 점검
    python run_once.py --force-rebalance  # 날짜 무시하고 즉시 리밸런싱 (테스트용)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

os.environ["IS_SIMULATION_MODE"] = "True"

from utils.logger import logger
from utils.broker_api_client import BrokerAPIClient
from quant_logic import TradingStrategy
import utils.screener as screener
from config import REBALANCE_EXIT_RANK, TOP_N_PORTFOLIO
from utils.universe import fetch_nasdaq100_universe


def main():
    is_news = "--news" in sys.argv
    is_force = "--force-rebalance" in sys.argv

    logger.info(f"[run_once] 시작 — 모드: {'뉴스 점검' if is_news else '강제 리밸런싱' if is_force else '전략 실행'}")

    user_id = os.getenv("BOT_USER_ID", "")
    broker = BrokerAPIClient(user_id=user_id)
    strategy = TradingStrategy(broker, user_id=user_id)

    if is_news:
        strategy.check_news_danger()
    elif is_force:
        # 현재 모멘텀 랭킹 산출 후 날짜 조건 없이 즉시 리밸런싱
        full_ranking = screener.run_momentum_screener(fetch_nasdaq100_universe(), top_n=REBALANCE_EXIT_RANK + 2)
        if not full_ranking:
            logger.error("[run_once] 랭킹 산출 실패, 종료합니다.")
            sys.exit(1)

        ranked_tickers = [r["ticker"] for r in full_ranking]
        new_top10 = ranked_tickers[:TOP_N_PORTFOLIO]
        current_prices = {}
        for sym in ranked_tickers:
            price_info = broker.get_current_price(sym)
            if price_info:
                current_prices[sym] = price_info.get("price")

        strategy.rebalancer.execute_rebalance(
            new_top10, current_prices,
            reason="강제 리밸런싱 테스트", force=True
        )
        import utils.supabase_client as supa
        holdings = strategy.rebalancer._get_holdings()
        supa.push_momentum_rankings(full_ranking, list(holdings.keys()))
    else:
        strategy.execute_strategy()

    logger.info("[run_once] 완료")


if __name__ == "__main__":
    main()
