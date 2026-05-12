#!/usr/bin/env python
"""
backtest.py — N10-MEW 전략 3년 백테스트
실행: python backtest.py
"""
import sys
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import date, timedelta

sys.path.insert(0, ".")
from config import UNIVERSE_TICKERS, MOMENTUM_PERIOD_DAYS, TOP_N_PORTFOLIO, WEIGHT_PER_STOCK

# ── 백테스트 설정 ─────────────────────────────────────────────────
BACKTEST_START   = date(2021, 5, 12)   # 투자 시작일 (5년 전)
BACKTEST_END     = date(2026, 5, 12)   # 종료일 (오늘)
INITIAL_KRW      = 1_000_000
KRW_USD_ENTRY    = 1_120               # 2021-05-12 기준 환율 (투자 시점)
KRW_USD_EXIT     = 1_370               # 2026-05-12 기준 환율 (회수 시점, 근사)
INITIAL_USD      = INITIAL_KRW / KRW_USD_ENTRY
SLIPPAGE         = 0.0005              # 거래당 편도 0.05% (수수료 + 슬리피지)
BENCHMARKS       = {
    "QQQ": "Nasdaq 100",
    "SPY": "S&P 500",
    "DIA": "Dow Jones",
}
RISK_FREE_ANNUAL = 0.05                # 연 5% (2023~2026 미국 단기 국채)


# ── 헬퍼 함수 ─────────────────────────────────────────────────────

def _trading_days_set(prices: pd.DataFrame) -> set:
    return {ts.date() for ts in prices.index}


def _first_trading_day(year: int, month: int, trading_days: set) -> date | None:
    d = date(year, month, 1)
    for _ in range(15):
        if d in trading_days:
            return d
        d += timedelta(days=1)
    return None


def _momentum_top10(prices: pd.DataFrame, as_of: pd.Timestamp) -> tuple[list, dict]:
    """as_of 시점 기준 63일 모멘텀 계산 후 Top 10 반환 (룩어헤드 바이어스 없음)"""
    scores = {}
    for ticker in UNIVERSE_TICKERS:
        if ticker not in prices.columns:
            continue
        series = prices[ticker].dropna()
        valid = series[series.index <= as_of]
        if len(valid) < MOMENTUM_PERIOD_DAYS:
            continue
        p_now  = float(valid.iloc[-1])
        p_past = float(valid.iloc[-MOMENTUM_PERIOD_DAYS])
        if p_past > 0:
            scores[ticker] = (p_now / p_past) - 1.0

    top10 = sorted(scores, key=scores.get, reverse=True)[:TOP_N_PORTFOLIO]
    return top10, scores


def _portfolio_value(holdings: dict, cash: float,
                     prices: pd.DataFrame, as_of: pd.Timestamp) -> float:
    total = cash
    for ticker, shares in holdings.items():
        if ticker in prices.columns:
            row = prices[ticker][prices.index <= as_of]
            if not row.empty:
                total += shares * float(row.iloc[-1])
    return total


def _rebalance(prices: pd.DataFrame, as_of: pd.Timestamp,
               holdings: dict, cash: float) -> tuple[dict, float, list, dict]:
    top10, scores = _momentum_top10(prices, as_of)
    total = _portfolio_value(holdings, cash, prices, as_of)
    target_per_stock = total * WEIGHT_PER_STOCK

    # 1단계: 탈락 종목 전량 매도
    for ticker in list(holdings.keys()):
        if ticker not in top10:
            row = prices[ticker][prices.index <= as_of]
            if not row.empty:
                proceeds = holdings[ticker] * float(row.iloc[-1]) * (1 - SLIPPAGE)
                cash += proceeds
            del holdings[ticker]

    # 2단계: 비중 조정 (과비중 → 매도, 과소비중/신규 → 매수)
    for ticker in top10:
        if ticker not in prices.columns:
            continue
        row = prices[ticker][prices.index <= as_of]
        if row.empty:
            continue
        cur_price = float(row.iloc[-1])
        cur_shares = holdings.get(ticker, 0.0)
        cur_value = cur_shares * cur_price
        diff = target_per_stock - cur_value

        if diff > 1.0:    # 매수
            buy_cost = diff * (1 + SLIPPAGE)
            if cash >= buy_cost:
                holdings[ticker] = cur_shares + diff / cur_price
                cash -= buy_cost
        elif diff < -1.0: # 매도
            sell_shares = abs(diff) / cur_price
            holdings[ticker] = cur_shares - sell_shares
            cash += abs(diff) * (1 - SLIPPAGE)

    return holdings, cash, top10, scores


# ── 메인 백테스트 ─────────────────────────────────────────────────

def run_backtest():
    print("=" * 64)
    print("  📊 N10-MEW 전략 백테스트 리포트")
    years_label = round((BACKTEST_END - BACKTEST_START).days / 365.25)
    print(f"  기간   : {BACKTEST_START} → {BACKTEST_END}  ({years_label}년)")
    print(f"  초기자본: ₩{INITIAL_KRW:,}  (환율 {KRW_USD_ENTRY}₩/$  ≈  ${INITIAL_USD:,.2f})")
    print("=" * 64)

    # ── 1. 데이터 다운로드 ────────────────────────────────────────
    data_from = BACKTEST_START - timedelta(days=int(MOMENTUM_PERIOD_DAYS * 1.8))
    all_tickers = UNIVERSE_TICKERS + list(BENCHMARKS.keys())
    bm_labels = "/".join(BENCHMARKS.keys())
    print(f"\n⏬  데이터 다운로드 중 ({len(UNIVERSE_TICKERS)}개 종목 + {bm_labels})...")

    raw = yf.download(
        all_tickers,
        start=str(data_from),
        end=str(BACKTEST_END + timedelta(days=1)),
        auto_adjust=True,
        progress=False,
    )
    prices = raw["Close"].ffill()
    print(f"    완료: {len(prices)}거래일  ({data_from} ~ {BACKTEST_END})\n")

    trading_days = _trading_days_set(prices)

    # ── 2. 리밸런싱 날짜 목록 생성 ────────────────────────────────
    # 첫 투자: BACKTEST_START 당일 (또는 가장 가까운 거래일)
    start_actual = BACKTEST_START
    while start_actual not in trading_days:
        start_actual += timedelta(days=1)

    rebalance_dates = [start_actual]

    # 이후: 매월 첫 영업일
    y, m = start_actual.year, start_actual.month
    while True:
        m += 1
        if m > 12:
            m, y = 1, y + 1
        if date(y, m, 1) > BACKTEST_END:
            break
        d = _first_trading_day(y, m, trading_days)
        if d and d <= BACKTEST_END:
            rebalance_dates.append(d)

    # ── 3. 일별 시뮬레이션 ────────────────────────────────────────
    holdings: dict = {}
    cash = INITIAL_USD
    daily_values: dict = {}
    rb_pointer = 0
    rebalance_log = []

    backtest_prices = prices.loc[pd.Timestamp(start_actual):]

    for ts in backtest_prices.index:
        d = ts.date()
        if d > BACKTEST_END:
            break

        # 리밸런싱 실행
        if rb_pointer < len(rebalance_dates) and d == rebalance_dates[rb_pointer]:
            holdings, cash, top10, scores = _rebalance(prices, ts, holdings, cash)
            val = _portfolio_value(holdings, cash, prices, ts)
            ret_pct = (val / INITIAL_USD - 1) * 100
            rebalance_log.append({
                "date": d,
                "top10": top10,
                "scores": scores,
                "value_usd": val,
                "ret_pct": ret_pct,
            })
            rb_pointer += 1

        # 일별 가치 집계
        total = cash
        for ticker, shares in holdings.items():
            if ticker in prices.columns and pd.notna(prices.loc[ts, ticker]):
                total += shares * float(prices.loc[ts, ticker])
        daily_values[d] = total

    # ── 4. 성과 지표 계산 ─────────────────────────────────────────
    pv = pd.Series(daily_values).sort_index()
    final_value = float(pv.iloc[-1])
    total_return = (final_value / INITIAL_USD - 1) * 100
    years = (BACKTEST_END - BACKTEST_START).days / 365.25
    cagr = ((final_value / INITIAL_USD) ** (1.0 / years) - 1) * 100

    daily_rets = pv.pct_change().dropna()
    sharpe = (
        (daily_rets.mean() - RISK_FREE_ANNUAL / 252)
        / daily_rets.std()
        * np.sqrt(252)
    ) if daily_rets.std() > 0 else 0.0

    cummax = pv.cummax()
    mdd = float(((pv - cummax) / cummax * 100).min())

    # 벤치마크 (각 지수 동일 기간 단순 보유)
    bm_results = {}
    for ticker, label in BENCHMARKS.items():
        if ticker not in prices.columns:
            continue
        bm_series = prices[ticker].dropna()
        bm_slice  = bm_series[bm_series.index.date >= start_actual]
        if bm_slice.empty:
            continue
        start_p = float(bm_slice.iloc[0])
        end_p   = float(bm_slice.iloc[-1])
        ret     = (end_p / start_p - 1) * 100
        bm_results[ticker] = {
            "label":     label,
            "return":    ret,
            "final_usd": INITIAL_USD * (end_p / start_p),
            "slice":     bm_slice,
        }
    # 하위 호환용 (차트에서 QQQ slice 사용)
    bm_slice = bm_results["QQQ"]["slice"] if "QQQ" in bm_results else pd.Series(dtype=float)

    # 원화 환산
    final_krw = final_value * KRW_USD_EXIT
    profit_krw = final_krw - INITIAL_KRW

    # ── 5. 리밸런싱 내역 출력 ─────────────────────────────────────
    print(f"{'─'*64}")
    print("  📅 월별 리밸런싱 내역 (Top 5 모멘텀 기준)")
    print(f"{'─'*64}")
    for log in rebalance_log:
        top5 = log["top10"][:5]
        scores = log["scores"]
        top5_str = "  ".join([f"{t}({scores.get(t,0)*100:+.0f}%)" for t in top5])
        print(
            f"  [{log['date']}]  ${log['value_usd']:>9,.2f}  {log['ret_pct']:>+7.2f}%"
            f"  │  {top5_str}"
        )

    # ── 6. 최종 결과 출력 ─────────────────────────────────────────
    print(f"\n{'='*64}")
    print("  📈 최종 성과 요약")
    print(f"{'='*64}")
    print(f"  {'항목':<20}  {'달러($)':>14}  {'원화(₩)':>16}")
    print(f"  {'─'*54}")
    print(f"  {'초기 자본':<20}  ${INITIAL_USD:>13,.2f}  ₩{INITIAL_KRW:>15,}")
    print(f"  {'최종 자산':<20}  ${final_value:>13,.2f}  ₩{final_krw:>15,.0f}")
    print(f"  {'순이익':<20}  ${(final_value-INITIAL_USD):>+13,.2f}  ₩{profit_krw:>+15,.0f}")
    print(f"\n  {'─'*54}")
    print(f"  {'총 수익률':<30}  {total_return:>+10.2f}%")
    print(f"  {'연평균 수익률(CAGR)':<30}  {cagr:>+10.2f}%")
    print(f"  {'최대 낙폭(MDD)':<30}  {mdd:>+10.2f}%")
    print(f"  {'샤프 지수':<30}  {sharpe:>10.2f}")
    print(f"\n  {'─'*54}")
    print(f"  {'지수 비교 (단순 보유)':<30}  {'수익률':>10}  {'최종 자산':>12}  {'초과 수익(α)':>12}")
    print(f"  {'·'*54}")
    for ticker, info in bm_results.items():
        alpha = total_return - info["return"]
        print(
            f"  {info['label']+' ('+ticker+')':<30}  {info['return']:>+9.2f}%"
            f"  ${info['final_usd']:>10,.2f}  {alpha:>+11.2f}%p"
        )
    print(f"  {'─'*54}")
    print(f"  ※ 환율: 매입 {KRW_USD_ENTRY}₩/$  →  매도 {KRW_USD_EXIT}₩/$")
    print(f"{'='*64}")

    # ── 7. 차트 저장 ──────────────────────────────────────────────
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9),
                                        gridspec_kw={"height_ratios": [3, 1]})
        fig.suptitle(f"N10-MEW Backtest  {BACKTEST_START} ~ {BACKTEST_END}  (5Y)"
                     f"  |  Initial: KRW {INITIAL_KRW:,} / ${INITIAL_USD:,.0f}",
                     fontsize=13, fontweight="bold")

        # 수익률 곡선
        norm_pv = pv / INITIAL_USD * 100
        date_index = pd.to_datetime(list(daily_values.keys()))

        ax1.plot(norm_pv.index, norm_pv.values, label="N10-MEW", color="#2196F3", linewidth=2.2)

        bm_styles = {
            "QQQ": ("#FF9800", "--", "Nasdaq 100 (QQQ)"),
            "SPY": ("#4CAF50", "-.", "S&P 500 (SPY)"),
            "DIA": ("#9C27B0", ":",  "Dow Jones (DIA)"),
        }
        for ticker, info in bm_results.items():
            color, ls, lbl = bm_styles.get(ticker, ("#888888", "--", ticker))
            bm_daily = info["slice"].reindex(date_index).ffill()
            norm_bm  = bm_daily / float(bm_daily.iloc[0]) * 100
            ax1.plot(norm_bm.index, norm_bm.values, label=lbl,
                     color=color, linewidth=1.5, linestyle=ls)

        # 리밸런싱 날짜 표시
        for log in rebalance_log:
            ax1.axvline(pd.Timestamp(log["date"]), color="gray", alpha=0.25, linewidth=0.7)

        ax1.axhline(100, color="black", linewidth=0.5, linestyle=":")
        ax1.set_ylabel("Portfolio Value (Initial = 100)")
        ax1.legend(loc="upper left")
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))

        # MDD 영역
        drawdown = (pv - pv.cummax()) / pv.cummax() * 100
        ax2.fill_between(drawdown.index, drawdown.values, 0, color="#F44336", alpha=0.5)
        ax2.set_ylabel("Drawdown (%)")
        ax2.set_xlabel("Date")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        chart_path = "backtest_result.png"
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"\n  📊 차트 저장 완료: {chart_path}")
    except Exception as e:
        print(f"\n  (차트 생성 건너뜀: {e})")


if __name__ == "__main__":
    run_backtest()
