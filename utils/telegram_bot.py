import os
import requests
from dotenv import load_dotenv
from utils.logger import logger

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str):
    """
    지정된 텔레그램 채팅방으로 메시지를 전송합니다.
    토큰이나 채팅 ID가 없으면 경고 로그를 남기고 스킵합니다.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.debug("[Telegram] 토큰 또는 채팅 ID가 없어 푸시 알림을 생략합니다.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML" # HTML 태그 (볼드체 등) 사용 가능
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.debug("[Telegram] 📱 스마트폰 푸시 알림 전송 성공!")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"[Telegram] ❌ 알림 전송 실패: {e}")
        return False
