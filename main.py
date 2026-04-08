# main.py
import schedule
import time
from dotenv import load_dotenv
from utils.logger import logger
from utils.broker_api_client import BrokerAPIClient
from quant_logic import TradingStrategy

def main():
    """
    프로그램의 메인 진입점입니다.
    환경 변수를 로드하고, API 클라이언트 및 전략을 초기화하며,
    전략 실행을 스케줄링합니다.
    """
    logger.info("주식 자동 매매 프로그램 시작합니다.")

    # .env 파일에서 환경 변수 로드
    load_dotenv()

    try:
        # 증권사 API 클라이언트 초기화
        broker_client = BrokerAPIClient()
        
        # 트레이딩 전략 초기화
        strategy = TradingStrategy(broker_client)

        # 퀀트 전략을 1분마다 실행하도록 스케줄링
        # 실제 운영에서는 증권사 API 호출 제한 등을 고려하여 간격을 조정해야 합니다.
        schedule.every(1).minutes.do(strategy.execute_strategy)
        logger.info("퀀트 전략이 1분마다 실행되도록 스케줄링되었습니다.")
        logger.info("프로그램이 실행 중입니다. Ctrl+C를 눌러 종료하세요.")

        # 프로그램 시작 시 1분 딜레이를 기다리지 않고 즉시 대시보드 및 전략을 1회 가동합니다.
        strategy.execute_strategy()

        while True:
            schedule.run_pending()
            time.sleep(1) # 1초마다 스케줄러 확인

    except Exception as e:
        logger.critical(f"프로그램 실행 중 치명적인 오류 발생: {e}", exc_info=True)
    finally:
        logger.info("주식 자동 매매 프로그램이 종료됩니다.")

if __name__ == "__main__":
    main()
