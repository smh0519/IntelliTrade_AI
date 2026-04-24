import threading
from datetime import datetime


class BotState:
    def __init__(self):
        self._lock = threading.Lock()
        self._is_active = True
        self._is_emergency = False
        self.start_time = datetime.now()

    @property
    def is_active(self):
        with self._lock:
            return self._is_active

    @property
    def is_emergency(self):
        with self._lock:
            return self._is_emergency

    def stop(self):
        with self._lock:
            self._is_active = False

    def resume(self):
        with self._lock:
            self._is_active = True
            self._is_emergency = False

    def emergency_stop(self):
        with self._lock:
            self._is_active = False
            self._is_emergency = True


bot_state = BotState()
