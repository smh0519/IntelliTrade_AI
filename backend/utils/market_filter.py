# utils/market_filter.py — 시장 국면 필터 (안전벨트)

import json
from enum import Enum
from datetime import datetime, date, timedelta
from pathlib import Path

import pytz
import yfinance as yf

from utils.logger import logger
from config import (
    MARKET_FILTER_SYMBOL, MARKET_FILTER_MA_PERIOD,
    MARKET_FILTER_BUFFER, EMERGENCY_EXIT_THRESHOLD,
    BULL_RECOVERY_CONFIRM_DAYS, EMERGENCY_SECOND_EXIT_DAYS,
    TIMEZONE,
)

STATE_FILE = Path(__file__).parent.parent / "data" / "market_state.json"


class MarketRegime(Enum):
    BULL      = "BULL"       # 정상 운용
    NEUTRAL   = "NEUTRAL"    # 신규 매수 중단
    CAUTION   = "CAUTION"    # 탈락 매도만 허용
    EMERGENCY = "EMERGENCY"  # 전 종목 긴급 청산


# ------------------------------------------------------------------ #
# 상태 영속화                                                          #
# ------------------------------------------------------------------ #

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[MarketFilter] 상태 파일 읽기 실패: {e}")
    return {
        "regime": MarketRegime.BULL.value,
        "bull_signal_start": None,
        "emergency_phase": 0,
        "emergency_first_exit_date": None,
    }


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


# ------------------------------------------------------------------ #
# 거래일 계산                                                          #
# ------------------------------------------------------------------ #

def _count_trading_days(start: date, end: date) -> int:
    """start ~ end 사이 영업일 수 (토/일 제외, 양 끝 포함)."""
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


# ------------------------------------------------------------------ #
# QQQ 신호 조회                                                        #
# ------------------------------------------------------------------ #

def get_qqq_signal() -> tuple[float, float] | None:
    """(QQQ 현재가, 200MA) 반환. 실패 시 None."""
    try:
        hist = yf.Ticker(MARKET_FILTER_SYMBOL).history(period="300d")
        if len(hist) < MARKET_FILTER_MA_PERIOD:
            logger.warning(f"[MarketFilter] 데이터 부족 ({len(hist)}일 < {MARKET_FILTER_MA_PERIOD}일)")
            return None
        price = float(hist["Close"].iloc[-1])
        ma200 = float(hist["Close"].tail(MARKET_FILTER_MA_PERIOD).mean())
        return price, ma200
    except Exception as e:
        logger.error(f"[MarketFilter] QQQ 데이터 조회 실패: {e}")
        return None


def _raw_regime(price: float, ma200: float) -> MarketRegime:
    """가격/MA 비율만으로 국면 판단 (복귀 확인 로직 없음)."""
    ratio = price / ma200
    if ratio >= 1 + MARKET_FILTER_BUFFER:
        return MarketRegime.BULL
    if ratio >= 1 - MARKET_FILTER_BUFFER:
        return MarketRegime.NEUTRAL
    if ratio >= 1 - EMERGENCY_EXIT_THRESHOLD:
        return MarketRegime.CAUTION
    return MarketRegime.EMERGENCY


# ------------------------------------------------------------------ #
# 국면 업데이트 (메인 진입점)                                           #
# ------------------------------------------------------------------ #

def update_regime() -> tuple[MarketRegime, MarketRegime, dict]:
    """
    QQQ 200MA를 기반으로 시장 국면을 갱신한다.
    반환: (이전 국면, 새 국면, state dict)
    """
    state = load_state()
    prev_regime = MarketRegime(state["regime"])
    today = datetime.now(pytz.timezone(TIMEZONE)).date()

    result = get_qqq_signal()
    if result is None:
        logger.warning("[MarketFilter] 신호 조회 실패 → 현재 국면 유지")
        return prev_regime, prev_regime, state

    price, ma200 = result
    raw = _raw_regime(price, ma200)

    logger.info(
        f"[MarketFilter] QQQ ${price:.2f} / 200MA ${ma200:.2f} "
        f"(비율 {price / ma200:.3f}) → 원시 국면: {raw.value}"
    )

    # ── BULL 복귀 확인 로직 ─────────────────────────────────────────
    if raw == MarketRegime.BULL and prev_regime != MarketRegime.BULL:
        if state["bull_signal_start"] is None:
            state["bull_signal_start"] = today.isoformat()
            logger.info(f"[MarketFilter] BULL 복귀 신호 시작: {today}")

        start = date.fromisoformat(state["bull_signal_start"])
        confirmed = _count_trading_days(start, today)

        if confirmed >= BULL_RECOVERY_CONFIRM_DAYS:
            new_regime = MarketRegime.BULL
            state["bull_signal_start"] = None
            logger.info(f"[MarketFilter] BULL 복귀 확인 완료 ({confirmed}거래일)")
        else:
            new_regime = prev_regime
            logger.info(
                f"[MarketFilter] BULL 복귀 확인 중 "
                f"({confirmed}/{BULL_RECOVERY_CONFIRM_DAYS}거래일)"
            )
    else:
        if raw != MarketRegime.BULL and state["bull_signal_start"] is not None:
            logger.info("[MarketFilter] BULL 신호 끊김 → 카운터 리셋")
            state["bull_signal_start"] = None
        new_regime = raw

    # ── EMERGENCY 해제 시 상태 초기화 ──────────────────────────────
    if prev_regime == MarketRegime.EMERGENCY and new_regime != MarketRegime.EMERGENCY:
        state["emergency_phase"] = 0
        state["emergency_first_exit_date"] = None
        logger.info("[MarketFilter] EMERGENCY 해제 → 청산 상태 초기화")

    state["regime"] = new_regime.value
    save_state(state)
    return prev_regime, new_regime, state


# ------------------------------------------------------------------ #
# EMERGENCY 2차 청산 시점 확인                                         #
# ------------------------------------------------------------------ #

def needs_second_emergency_exit(state: dict) -> bool:
    """EMERGENCY 2차 청산(나머지 30%) 시점인지 확인."""
    if state.get("emergency_phase") != 1:
        return False
    first_exit = state.get("emergency_first_exit_date")
    if not first_exit:
        return False
    start = date.fromisoformat(first_exit)
    today = datetime.now(pytz.timezone(TIMEZONE)).date()
    elapsed = _count_trading_days(start, today) - 1  # 당일 제외
    return elapsed >= EMERGENCY_SECOND_EXIT_DAYS
