# main.py
import sys
import schedule
import time
from dotenv import load_dotenv
from utils.logger import logger
from utils.broker_api_client import BrokerAPIClient
from utils.bot_state import bot_state
from utils.telegram_bot import send_telegram_message, TelegramCommandHandler
from quant_logic import TradingStrategy


def main():
    logger.info("주식 자동 매매 프로그램 시작합니다.")

    load_dotenv()

    # 텔레그램 부팅 알림
    send_telegram_message(
        "🤖 <b>[IntelliTrade AI 시스템 부팅]</b>\n\n"
        "텔레그램 연동 성공! 자동 매매 봇이 정상적으로 가동되어 "
        "지금부터 뉴욕 증시 감시를 시작합니다. 🚀\n\n"
        "📋 /help 로 명령어 목록을 확인하세요."
    )

    # 텔레그램 명령어 폴링 핸들러 시작 (데몬 스레드)
    cmd_handler = TelegramCommandHandler(bot_state)
    cmd_handler.start_polling()

    try:
        broker_client = BrokerAPIClient()
        strategy = TradingStrategy(broker_client)

        def run_strategy_if_active():
            if bot_state.is_active:
                strategy.execute_strategy()
            else:
                logger.info("[스케줄러] 봇 일시정지 상태 — 전략 실행 건너뜀")

        def run_news_check_if_active():
            if bot_state.is_active:
                strategy.check_news_danger()
            else:
                logger.info("[스케줄러] 봇 일시정지 상태 — 뉴스 감식 건너뜀")

        schedule.every(1).minutes.do(run_strategy_if_active)
        logger.info("퀀트 전략이 1분마다 실행되도록 스케줄링되었습니다.")

        schedule.every(1).hours.do(run_news_check_if_active)
        logger.info("AI 뉴스 마크맨이 1시간 주기로 뉴스 감식을 진행하도록 세팅되었습니다.")

        logger.info("프로그램이 실행 중입니다. Ctrl+C를 눌러 종료하세요.")

        # 최초 1회 즉시 실행
        strategy.check_news_danger()
        strategy.execute_strategy()

        while True:
            # 긴급 정지 플래그 감지 시 즉시 종료
            if bot_state.is_emergency:
                logger.critical("[긴급 정지] 텔레그램 명령으로 강제 종료합니다.")
                send_telegram_message("🚨 <b>프로그램이 강제 종료되었습니다.</b>")
                sys.exit(1)

            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("사용자가 프로그램을 종료했습니다 (Ctrl+C).")
        send_telegram_message("🛑 <b>봇이 수동 종료되었습니다.</b> (Ctrl+C)")
    except Exception as e:
        logger.critical(f"프로그램 실행 중 치명적인 오류 발생: {e}", exc_info=True)
    finally:
        logger.info("주식 자동 매매 프로그램이 종료됩니다.")


if __name__ == "__main__":
    main()
