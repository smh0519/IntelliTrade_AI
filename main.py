import time
from datetime import datetime
from config.settings import IS_SIMULATION_MODE
from utils.api_handler import APIHandler
from utils.notifier import Notifier
from quant_logic import QuantStrategy
# from gemini_pro import GeminiPro  # Gemini Pro 연동 시 주석 해제

def main():
    """
    주식 자동 매매 프로그램의 메인 실행 함수입니다.
    """
    print("--------------------------------------------------")
    print("📈 주식 자동 매매 시스템 시작")
    print(f"시뮬레이션 모드: {IS_SIMULATION_MODE}")
    print("--------------------------------------------------")

    # 1. 모듈 초기화
    api_handler = APIHandler()
    notifier = Notifier()
    quant_strategy = QuantStrategy(api_handler, notifier)
    # gemini_pro_client = GeminiPro() # Gemini Pro 연동 시 초기화

    # 감시할 종목 목록 (예시)
    # TODO: 실제 감시할 종목 목록으로 변경하거나, DB/파일에서 로드하도록 구현
    WATCHLIST = ["005930", "000660"] # 삼성전자, SK하이닉스 (종목 코드는 한국거래소 기준)

    # 2. 초기 보유 종목 정보 업데이트
    quant_strategy.update_holdings()

    # 3. 메인 자동 매매 루프
    # 실제 운영 시에는 시장 개장 시간 동안만 동작하도록 스케줄링 필요
    # 여기서는 예시를 위해 무한 루프
    try:
        while True:
            current_time = datetime.now()
            print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 자동 매매 루프 시작...")

            # TODO: 실제 거래 시간 확인 로직 추가
            # if not is_market_open(current_time):
            #     print("시장이 닫혔습니다. 다음 개장 시간까지 대기합니다.")
            #     time.sleep(60 * 60) # 1시간 대기
            #     continue

            for symbol in WATCHLIST:
                print(f"--- 종목 분석 및 매매 결정: {symbol} ---")
                quant_strategy.make_decision_and_execute(symbol)
                time.sleep(5) # 각 종목 처리 후 잠시 대기 (API 호출 제한 방지)

            print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 자동 매매 루프 완료. 다음 주기 대기...")
            time.sleep(60 * 5) # 5분마다 반복 (실제 운영 시 더 길게 설정 가능)

    except KeyboardInterrupt:
        print("\n[!] 사용자 요청으로 자동 매매 시스템을 종료합니다.")
        notifier.notify_info("자동 매매 시스템 종료 (수동 종료).")
    except Exception as e:
        print(f"[ERROR] 예기치 않은 오류 발생: {e}")
        notifier.notify_error(f"예기치 않은 오류 발생: {e}")
    finally:
        print("시스템 종료.")

if __name__ == "__main__":
    main()
