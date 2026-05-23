"use client";

import { useState, useEffect } from "react";
import PortfolioSummary from "@/components/PortfolioSummary";
import HoldingsList from "@/components/HoldingsList";
import MomentumRankingCard from "@/components/MomentumRanking";
import RebalanceStatus from "@/components/RebalanceStatus";
import BottomNav from "@/components/BottomNav";
import NewsPage from "@/components/NewsPage";
import { fetchDashboardData } from "@/lib/api";
import { DashboardData } from "@/lib/types";
import { MOCK_DATA } from "@/lib/mockData";

type Tab = "overview" | "holdings" | "momentum" | "rebalance" | "news";

export default function Home() {
  const [tab, setTab] = useState<Tab>("overview");
  const [data, setData] = useState<DashboardData>(MOCK_DATA);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData().then((d) => {
      setData(d);
      setLoading(false);
    });
    // 5분마다 자동 갱신
    const interval = setInterval(() => {
      fetchDashboardData().then(setData);
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const { portfolio, momentum_ranking, rebalance_info, benchmarks, earnings_alerts } = data;
  const qqq = benchmarks.find((b) => b.ticker === "QQQ")?.return_pct ?? 0;
  const alpha = portfolio.total_pnl_pct - qqq;

  return (
    <main className="min-h-screen bg-slate-950 pb-24">
      {/* Header */}
      <header className="safe-area-pt sticky top-0 z-10 bg-slate-950/90 backdrop-blur border-b border-slate-800 px-4 pb-3">
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-base font-bold tracking-tight">IntelliTrade AI</h1>
            <p className="text-xs text-slate-500">
              {tab === "news" ? "오늘의 마켓 이슈" : "N10-MEW · 모의투자"}
            </p>
          </div>
          {loading ? (
            <span className="text-xs text-slate-500 animate-pulse">불러오는 중...</span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live
            </span>
          )}
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 pt-4 space-y-4">
        {tab === "overview" && (
          <>
            <PortfolioSummary portfolio={portfolio} />

            {/* Quick stats */}
            <div className="grid grid-cols-3 gap-3">
              <QuickStat
                label="투자 수익"
                value={`${portfolio.total_pnl_pct >= 0 ? "+" : ""}${portfolio.total_pnl_pct.toFixed(2)}%`}
                color={portfolio.total_pnl_pct >= 0 ? "text-emerald-400" : "text-red-400"}
              />
              <QuickStat
                label="vs QQQ"
                value={`${alpha >= 0 ? "+" : ""}${alpha.toFixed(1)}%p`}
                color={alpha >= 0 ? "text-blue-400" : "text-red-400"}
              />
              <QuickStat
                label="다음 리밸"
                value={rebalance_info.next_rebalance_date.slice(5)}
                color="text-slate-300"
              />
            </div>

            {/* Top 5 momentum preview */}
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-3">
                모멘텀 Top 5
              </p>
              <div className="flex gap-2 flex-wrap">
                {momentum_ranking.slice(0, 5).map((m) => (
                  <span
                    key={m.ticker}
                    className={`text-xs font-mono px-2.5 py-1 rounded-lg ${
                      m.in_portfolio
                        ? "bg-blue-900/50 text-blue-300 border border-blue-800/50"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    #{m.rank} {m.ticker}{" "}
                    <span className="text-emerald-400">+{m.momentum_pct.toFixed(1)}%</span>
                  </span>
                ))}
              </div>
            </div>

            {/* Earnings alerts */}
            {earnings_alerts.length > 0 && (
              <div className="rounded-2xl bg-amber-950/30 border border-amber-800/50 p-4">
                <p className="text-xs text-amber-400 uppercase tracking-widest mb-3 font-semibold">
                  실적 발표 예정
                </p>
                <div className="space-y-2">
                  {earnings_alerts.map((a) => (
                    <div key={a.ticker} className="flex items-center justify-between">
                      <span className="text-sm font-semibold">{a.ticker}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400">
                          {a.earnings_date.slice(5).replace("-", "/")}
                        </span>
                        <span className={`text-xs font-mono px-2 py-0.5 rounded-md font-semibold ${
                          a.days_until === 0
                            ? "bg-red-900/60 text-red-300"
                            : "bg-amber-900/60 text-amber-300"
                        }`}>
                          {a.days_until === 0 ? "D-Day" : `D-${a.days_until}`}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Drift alert */}
            {rebalance_info.drift_alerts.length > 0 && (
              <div className="rounded-2xl bg-amber-950/40 border border-amber-800/50 p-4 flex items-start gap-3">
                <span className="text-amber-400 text-lg flex-shrink-0">⚠️</span>
                <div>
                  <p className="text-sm font-semibold text-amber-300">랭킹 이탈 경보</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {rebalance_info.drift_alerts.join(", ")} 종목이 12위 밖으로 이탈했습니다.
                    다음 사이클에 자동 교체됩니다.
                  </p>
                </div>
              </div>
            )}
          </>
        )}

        {tab === "holdings" && <HoldingsList positions={portfolio.positions} />}
        {tab === "momentum" && <MomentumRankingCard ranking={momentum_ranking} />}
        {tab === "rebalance" && (
          <RebalanceStatus
            info={rebalance_info}
            benchmarks={benchmarks}
            strategyReturn={portfolio.total_pnl_pct}
          />
        )}
        {tab === "news" && <NewsPage />}
      </div>

      <BottomNav active={tab} onChange={(t) => setTab(t as Tab)} />
    </main>
  );
}

function QuickStat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="rounded-xl bg-slate-900 border border-slate-800 p-3 text-center">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-sm font-bold font-mono ${color}`}>{value}</p>
    </div>
  );
}
