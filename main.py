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
    logger.info("IntelliTrade AI (N10-MEW) 시작합니다.")
    load_dotenv()

    send_telegram_message(
        "🤖 <b>[IntelliTrade AI N10-MEW 부팅 완료]</b>\n\n"
        "📊 <b>전략:</b> Nasdaq 10 Momentum Equal Weight\n"
        "🎯 <b>유니버스:</b> 나스닥 100 시가총액 상위 50\n"
        "🔄 <b>리밸런싱:</b> 매월 첫 영업일 10:00 AM (NY)\n"
        "🤖 <b>Physical AI 테마 우대 적용 중</b>\n\n"
        "📋 /help 로 명령어 목록을 확인하세요."
    )

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

        # N10-MEW: 1시간마다 랭킹 체크 (월 첫 영업일에 자동 리밸런싱, 이탈 감지)
        schedule.every(1).hours.do(run_strategy_if_active)
        logger.info("N10-MEW 전략이 1시간마다 실행되도록 스케줄링되었습니다.")

        # 뉴스 점검: 매주 월요일 09:00 (주간 1회)
        schedule.every().monday.at("09:00").do(run_news_check_if_active)
        logger.info("AI 뉴스 점검이 매주 월요일 09:00에 실행되도록 스케줄링되었습니다.")

        logger.info("프로그램이 실행 중입니다. Ctrl+C를 눌러 종료하세요.")

        # 최초 1회 즉시 실행
        strategy.execute_strategy()

        while True:
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
        logger.info("IntelliTrade AI N10-MEW 종료됩니다.")


if __name__ == "__main__":
    main()
