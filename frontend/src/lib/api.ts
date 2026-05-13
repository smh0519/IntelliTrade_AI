import { supabase } from "./supabase";
import { DashboardData, Position, MomentumRanking } from "./types";
import { MOCK_DATA } from "./mockData";

// Supabase가 설정되지 않은 경우 목데이터로 폴백
function isMockMode() {
  return (
    !process.env.NEXT_PUBLIC_SUPABASE_URL ||
    process.env.NEXT_PUBLIC_SUPABASE_URL === "https://your-project-id.supabase.co"
  );
}

export async function fetchDashboardData(): Promise<DashboardData> {
  if (isMockMode()) return MOCK_DATA;

  try {
    const [snapshotRes, rankingRes, rebalanceRes] = await Promise.all([
      supabase
        .from("portfolio_snapshots")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(1)
        .single(),
      supabase
        .from("momentum_rankings")
        .select("rankings, created_at")
        .order("created_at", { ascending: false })
        .limit(1)
        .single(),
      supabase
        .from("rebalance_log")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(1)
        .single(),
    ]);

    // ── 포트폴리오 ────────────────────────────────────────────────
    const snap = snapshotRes.data;
    const positionsRaw: Record<string, { qty: number; avg_price: number; current_price: number }> =
      snap?.positions ?? {};

    const totalValue = snap?.total_value ?? 0;
    const positions: Position[] = Object.entries(positionsRaw).map(([ticker, info]) => {
      const value = info.qty * info.current_price;
      return {
        ticker,
        qty: info.qty,
        avg_price: info.avg_price,
        current_price: info.current_price,
        value,
        pnl_pct: info.avg_price > 0
          ? ((info.current_price - info.avg_price) / info.avg_price) * 100
          : 0,
        weight: totalValue > 0 ? (value / totalValue) * 100 : 0,
      };
    });

    // ── 모멘텀 랭킹 ───────────────────────────────────────────────
    const rawRankings: { rank: number; ticker: string; in_portfolio: boolean }[] =
      rankingRes.data?.rankings ?? [];
    const momentum_ranking: MomentumRanking[] = rawRankings.map((r) => ({
      rank:         r.rank,
      ticker:       r.ticker,
      momentum_pct: 0,   // 현재 스키마에는 없음 — 다음 버전에서 추가 예정
      in_portfolio: r.in_portfolio,
    }));

    // ── 리밸런싱 정보 ─────────────────────────────────────────────
    const lastRB = rebalanceRes.data;
    const lastDate = lastRB?.created_at
      ? new Date(lastRB.created_at).toISOString().slice(0, 10)
      : null;
    const nextDate = lastDate ? getNextFirstTradingDay(new Date(lastDate)) : "—";

    return {
      portfolio: {
        initial_cash:  snap?.initial_cash ?? 1000,
        cash:          snap?.cash ?? 0,
        currency:      "USD",
        total_value:   snap?.total_value ?? 0,
        total_pnl_pct: snap?.pnl_pct ?? 0,
        positions,
        last_updated:  snap?.created_at
          ? new Date(snap.created_at).toLocaleString("ko-KR", { timeZone: "America/New_York" }) + " (뉴욕)"
          : "—",
      },
      momentum_ranking,
      rebalance_info: {
        last_rebalance_date: lastDate,
        next_rebalance_date: nextDate,
        drift_alerts:        [],
        status:              "healthy",
      },
      news_alerts: [],
      benchmarks:  MOCK_DATA.benchmarks,  // 벤치마크는 별도 API 필요 (추후 연동)
    };
  } catch (e) {
    console.error("[fetchDashboardData] Supabase 오류, 목데이터로 폴백:", e);
    return MOCK_DATA;
  }
}

// 해당 날짜 다음 달 첫 영업일(월~금) 계산
function getNextFirstTradingDay(lastRebalance: Date): string {
  const d = new Date(lastRebalance);
  d.setMonth(d.getMonth() + 1, 1);
  while (d.getDay() === 0 || d.getDay() === 6) {
    d.setDate(d.getDate() + 1);
  }
  return d.toISOString().slice(0, 10);
}
