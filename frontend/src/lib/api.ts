import { DashboardData, Position, MomentumRanking, EarningsAlert } from "./types";
import { MOCK_DATA } from "./mockData";

export async function fetchDashboardData(): Promise<DashboardData> {
  try {
    const res = await fetch("/api/dashboard", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const { snapshot, ranking, rebalance, benchmarks: apiBenchmarks } = await res.json();

    if (!snapshot) return MOCK_DATA;

    // ── 포트폴리오 ─────────────────────────────────────────────────
    const positionsRaw: Record<
      string,
      { qty: number; avg_price: number; current_price: number; earnings_date?: string | null }
    > = snapshot.positions ?? {};

    // 주식 평가액 / 실제 매수금액 — 현금 제외
    const stockValue = Object.values(positionsRaw).reduce(
      (s, info) => s + info.qty * info.current_price, 0
    );
    const investedAmount = Object.values(positionsRaw).reduce(
      (s, info) => s + info.qty * info.avg_price, 0
    );

    const positions: Position[] = Object.entries(positionsRaw).map(
      ([ticker, info]) => {
        const value = info.qty * info.current_price;
        return {
          ticker,
          qty:           info.qty,
          avg_price:     info.avg_price,
          current_price: info.current_price,
          value,
          pnl_pct:
            info.avg_price > 0
              ? ((info.current_price - info.avg_price) / info.avg_price) * 100
              : 0,
          weight:        stockValue > 0 ? (value / stockValue) * 100 : 0,
          earnings_date: info.earnings_date ?? null,
        };
      }
    );

    // ── 실적 발표 알림 (7일 이내) ──────────────────────────────────
    const todayMs = new Date().setHours(0, 0, 0, 0);
    const earnings_alerts: EarningsAlert[] = positions
      .filter((p) => p.earnings_date != null)
      .map((p) => {
        const days_until = Math.ceil(
          (new Date(p.earnings_date!).getTime() - todayMs) / 86400000
        );
        return { ticker: p.ticker, earnings_date: p.earnings_date!, days_until };
      })
      .filter((a) => a.days_until >= 0 && a.days_until <= 7)
      .sort((a, b) => a.days_until - b.days_until);

    // ── 모멘텀 랭킹 ────────────────────────────────────────────────
    const rawRankings: { rank: number; ticker: string; momentum_pct: number; in_portfolio: boolean }[] =
      ranking?.rankings ?? [];
    const momentum_ranking: MomentumRanking[] = rawRankings.map((r) => ({
      rank:         r.rank,
      ticker:       r.ticker,
      momentum_pct: r.momentum_pct ?? 0,
      in_portfolio: r.in_portfolio,
    }));

    // ── 리밸런싱 정보 ──────────────────────────────────────────────
    const lastDate = rebalance?.created_at
      ? new Date(rebalance.created_at).toISOString().slice(0, 10)
      : null;
    const nextDate = lastDate
      ? getNextFirstTradingDay(new Date(lastDate))
      : "—";

    const lastUpdated = snapshot.created_at
      ? new Date(snapshot.created_at).toLocaleString("ko-KR", {
          timeZone: "America/New_York",
          year: "numeric", month: "2-digit", day: "2-digit",
          hour: "2-digit", minute: "2-digit",
        }) + " (뉴욕)"
      : "—";

    return {
      portfolio: {
        initial_cash:    snapshot.initial_cash ?? 1000,
        cash:            snapshot.cash ?? 0,
        currency:        "USD",
        invested_amount: investedAmount,
        total_value:     stockValue,
        total_pnl_pct:
          investedAmount > 0
            ? ((stockValue - investedAmount) / investedAmount) * 100
            : 0,
        positions,
        last_updated: lastUpdated,
      },
      momentum_ranking,
      rebalance_info: {
        last_rebalance_date: lastDate,
        next_rebalance_date: nextDate,
        drift_alerts:        [],
        status:              "healthy",
      },
      news_alerts:     [],
      benchmarks:      Array.isArray(apiBenchmarks) && apiBenchmarks.length > 0
        ? apiBenchmarks
        : MOCK_DATA.benchmarks,
      earnings_alerts,
    };
  } catch (e) {
    console.error("[fetchDashboardData] 오류, 목데이터로 폴백:", e);
    return MOCK_DATA;
  }
}

function getNextFirstTradingDay(lastRebalance: Date): string {
  const d = new Date(lastRebalance);
  d.setMonth(d.getMonth() + 1, 1);
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}
