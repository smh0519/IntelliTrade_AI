"""
GitHub Actions용 단일 실행 runner.
전략 1사이클을 실행하고 종료 (무한 루프 없음, Telegram 폴링 없음).

Usage:
    python run_once.py           # 전략 실행
    python run_once.py --news    # 뉴스 악재 점검
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# 시뮬레이션 모드 강제 설정
os.environ["IS_SIMULATION_MODE"] = "True"

from utils.logger import logger
from utils.broker_api_client import BrokerAPIClient
from quant_logic import TradingStrategy


def main():
    mode = "--news" in sys.argv
    logger.info(f"[run_once] 시작 — 모드: {'뉴스 점검' if mode else '전략 실행'}")

    broker = BrokerAPIClient()
    strategy = TradingStrategy(broker)

    if mode:
        strategy.check_news_danger()
    else:
        strategy.execute_strategy()

    logger.info("[run_once] 완료")


if __name__ == "__main__":
    main()
