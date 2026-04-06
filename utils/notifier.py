import logging
import requests
import json
from config import settings

logger = logging.getLogger(__name__)

class Notifier:
    """
    다양한 채널로 알림을 전송하는 클래스.
    현재는 콘솔, 슬랙, 텔레그램을 지원합니다.
    """
    def __init__(self):
        self.slack_webhook_url = settings.SLACK_WEBHOOK_URL if hasattr(settings, 'SLACK_WEBHOOK_URL') else None
        self.telegram_bot_token = settings.TELEGRAM_BOT_TOKEN if hasattr(settings, 'TELEGRAM_BOT_TOKEN') else None
        self.telegram_chat_id = settings.TELEGRAM_CHAT_ID if hasattr(settings, 'TELEGRAM_CHAT_ID') else None

        if not self.slack_webhook_url:
            logger.info("Slack webhook URL not configured in settings.")
        if not (self.telegram_bot_token and self.telegram_chat_id):
            logger.info("Telegram bot token or chat ID not configured in settings.")

    def _send_slack_message(self, message):
        """Slack으로 메시지를 전송합니다."""
        if not self.slack_webhook_url:
            logger.debug("Slack webhook URL is not set. Skipping Slack notification.")
            return

        headers = {'Content-type': 'application/json'}
        payload = {'text': message}
        try:
            response = requests.post(self.slack_webhook_url, headers=headers, data=json.dumps(payload), timeout=5)
            response.raise_for_status()
            logger.info("Message successfully sent to Slack.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to Slack: {e}")

    def _send_telegram_message(self, message):
        """Telegram으로 메시지를 전송합니다."""
        if not (self.telegram_bot_token and self.telegram_chat_id):
            logger.debug("Telegram bot token or chat ID is not set. Skipping Telegram notification.")
            return

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': message,
            'parse_mode': 'Markdown' # 메시지 포맷팅을 위해 Markdown 사용
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            logger.info("Message successfully sent to Telegram.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to Telegram: {e}")

    def send_notification(self, message, channel="all"):
        """
        지정된 채널 또는 모든 설정된 채널로 알림을 전송합니다.
        Args:
            message (str): 전송할 메시지 내용.
            channel (str): 'console', 'slack', 'telegram', 'all' 중 하나.
        """
        log_message = f"[NOTIFICATION] {message}"
        logger.info(log_message) # 모든 알림은 기본적으로 로그로 남깁니다.

        if channel == "console" or channel == "all":
            print(f"🔔 {message}")

        if channel == "slack" or channel == "all":
            self._send_slack_message(message)

        if channel == "telegram" or channel == "all":
            self._send_telegram_message(message)

# 전역 Notifier 인스턴스 (옵션)
# from utils.notifier import notifier
# notifier.send_notification("Hello!")
notifier = Notifier()
