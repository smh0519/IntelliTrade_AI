import os
import time
import threading
import requests
from datetime import datetime
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
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.debug("[Telegram] 📱 스마트폰 푸시 알림 전송 성공!")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"[Telegram] ❌ 알림 전송 실패: {e}")
        return False


class TelegramCommandHandler:
    """
    텔레그램 명령어 폴링 핸들러.
    별도 데몬 스레드에서 2초마다 업데이트를 확인하고 명령어를 처리합니다.

    지원 명령어:
      /start     - 봇 가동 (일시정지 해제와 동일)
      /stop      - 봇 일시정지
      /resume    - 봇 재가동
      /status    - 현재 상태 및 가동 시간 조회
      /emergency - 긴급 강제 정지 (프로세스 종료)
    """

    HELP_TEXT = (
        "📋 <b>사용 가능한 명령어</b>\n\n"
        "/start — 봇 가동\n"
        "/stop — 봇 일시정지\n"
        "/resume — 봇 재가동\n"
        "/status — 현재 상태 확인\n"
        "/emergency — 긴급 강제 정지\n"
    )

    def __init__(self, state):
        self._state = state
        self._offset = 0

    def start_polling(self):
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()
        logger.info("[Telegram] 명령어 폴링 핸들러 시작 (2초 간격)")

    # ── 내부 메서드 ──────────────────────────────────────────

    def _poll_loop(self):
        backoff = 2
        fail_count = 0
        while True:
            try:
                self._fetch_and_handle()
                # 성공 시 백오프 리셋
                if backoff > 2:
                    logger.info("[Telegram] 연결 복구됨. 폴링 정상화.")
                backoff = 2
                fail_count = 0
            except Exception as e:
                fail_count += 1
                if fail_count <= 3:
                    logger.error(f"[Telegram] 폴링 오류: {e}")
                elif fail_count == 4:
                    logger.warning(
                        f"[Telegram] 연속 {fail_count}회 실패. "
                        f"연결 복구될 때까지 로그를 줄입니다. (재시도 간격: {backoff}초)"
                    )
                # 3회 초과 시 로그 생략 (60초마다 1회만 상태 출력)
                elif fail_count % 30 == 0:
                    logger.warning(
                        f"[Telegram] 여전히 연결 불가. 연속 {fail_count}회 실패 중..."
                    )
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)  # 최대 60초
                continue
            time.sleep(2)

    def _fetch_and_handle(self):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"offset": self._offset, "timeout": 1}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if not data.get("ok"):
            return

        for update in data.get("result", []):
            self._offset = update["update_id"] + 1
            self._handle_update(update)

    def _handle_update(self, update):
        message = update.get("message", {})
        text = message.get("text", "").strip()
        chat_id = str(message.get("chat", {}).get("id", ""))

        if not text or not chat_id:
            return

        # 등록된 채팅 ID만 허용 (보안)
        if chat_id != str(TELEGRAM_CHAT_ID):
            logger.warning(f"[Telegram] 미등록 chat_id({chat_id}) 접근 차단")
            return

        command = text.split()[0].lower()
        logger.info(f"[Telegram] 명령어 수신: {command}")

        handlers = {
            "/start":     self._cmd_start,
            "/stop":      self._cmd_stop,
            "/resume":    self._cmd_resume,
            "/status":    self._cmd_status,
            "/emergency": self._cmd_emergency,
            "/help":      self._cmd_help,
        }

        handler = handlers.get(command)
        if handler:
            handler()
        else:
            send_telegram_message(
                f"❓ 알 수 없는 명령어: <code>{command}</code>\n\n" + self.HELP_TEXT
            )

    # ── 명령어 핸들러 ─────────────────────────────────────────

    def _cmd_start(self):
        self._state.resume()
        send_telegram_message(
            "✅ <b>봇 가동</b>\n\n자동 매매 전략이 활성화되었습니다."
        )

    def _cmd_stop(self):
        self._state.stop()
        send_telegram_message(
            "⏸ <b>봇 일시정지</b>\n\n"
            "자동 매매 전략이 중단되었습니다.\n"
            "/resume 으로 재가동할 수 있습니다."
        )

    def _cmd_resume(self):
        self._state.resume()
        send_telegram_message(
            "▶️ <b>봇 재가동</b>\n\n자동 매매 전략이 다시 활성화되었습니다."
        )

    def _cmd_status(self):
        is_active = self._state.is_active
        status_icon = "🟢 활성" if is_active else "🔴 정지"
        uptime = str(datetime.now() - self._state.start_time).split(".")[0]
        send_telegram_message(
            f"📊 <b>봇 상태 보고</b>\n\n"
            f"상태: {status_icon}\n"
            f"가동 시간: {uptime}"
        )

    def _cmd_emergency(self):
        self._state.emergency_stop()
        send_telegram_message(
            "🚨 <b>긴급 정지 실행!</b>\n\n"
            "모든 전략이 즉시 중단됩니다.\n"
            "프로그램이 강제 종료됩니다."
        )

    def _cmd_help(self):
        send_telegram_message(self.HELP_TEXT)
