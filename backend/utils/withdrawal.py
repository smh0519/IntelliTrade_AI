import os
import json
from utils.logger import logger

DATA_FILE = "data/withdrawal_reservation.json"


def _load() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"amount": None}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"amount": None}


def _save(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def set_reservation(amount: float):
    """다음 리밸런싱 시 출금할 금액을 예약합니다."""
    _save({"amount": round(amount, 4)})
    logger.info(f"[Withdrawal] 출금 예약 설정: ${amount:.2f}")


def get_reservation() -> float | None:
    """예약된 출금 금액을 반환합니다. 예약 없으면 None."""
    return _load().get("amount")


def clear_reservation():
    """리밸런싱 완료 후 예약을 초기화합니다."""
    _save({"amount": None})
    logger.info("[Withdrawal] 출금 예약 초기화 완료")
