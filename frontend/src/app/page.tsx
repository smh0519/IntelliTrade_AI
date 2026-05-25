"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { User, LogOut, X } from "lucide-react";
import PortfolioSummary from "@/components/PortfolioSummary";
import HoldingsList from "@/components/HoldingsList";
import MomentumRankingCard from "@/components/MomentumRanking";
import RebalanceStatus from "@/components/RebalanceStatus";
import BottomNav from "@/components/BottomNav";
import NewsPage from "@/components/NewsPage";
import BrokerSettings from "@/components/BrokerSettings";
import WithdrawalReservation from "@/components/WithdrawalReservation";
import { fetchDashboardData, fetchLivePrices } from "@/lib/api";
import { DashboardData } from "@/lib/types";
import { MOCK_DATA } from "@/lib/mockData";
import { createBrowserSupabaseClient } from "@/lib/supabase";

type Tab = "overview" | "holdings" | "momentum" | "rebalance" | "news";

export default function Home() {
  const router = useRouter();
  const supabase = createBrowserSupabaseClient();

  const [tab, setTab] = useState<Tab>("overview");
  const [data, setData] = useState<DashboardData>(MOCK_DATA);
  const [loading, setLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // 유저 정보 로드
  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) { router.replace("/login"); return; }
      setUserEmail(user.email ?? null);
      setUserId(user.id);
    });
  }, [router, supabase.auth]);

  // 대시보드 데이터 로드
  useEffect(() => {
    // 초기 전체 데이터 로드
    fetchDashboardData().then((d) => {
      setData(d);
      setLoading(false);
    });

    // 5분마다 현재가·수익률·평가액 갱신
    const priceInterval = setInterval(async () => {
      const prices = await fetchLivePrices();
      if (Object.keys(prices).length === 0) return;
      setData((prev) => {
        const positions = prev.portfolio.positions.map((p) => {
          const cur = prices[p.ticker] ?? p.current_price;
          const value = p.qty * cur;
          return {
            ...p,
            current_price: cur,
            value,
            pnl_pct: p.avg_price > 0 ? ((cur - p.avg_price) / p.avg_price) * 100 : 0,
          };
        });
        const stockValue = positions.reduce((s, p) => s + p.value, 0);
        const investedAmount = positions.reduce((s, p) => s + p.qty * p.avg_price, 0);
        return {
          ...prev,
          portfolio: {
            ...prev.portfolio,
            total_value: stockValue,
            total_pnl_pct:
              investedAmount > 0 ? ((stockValue - investedAmount) / investedAmount) * 100 : 0,
            positions: positions.map((p) => ({
              ...p,
              weight: stockValue > 0 ? (p.value / stockValue) * 100 : 0,
            })),
          },
        };
      });
    }, 5 * 60 * 1000);

    // 15분마다 전체 데이터 갱신 (보유 수량·평단가·모멘텀 랭킹 포함)
    const fullInterval = setInterval(() => {
      fetchDashboardData().then(setData);
    }, 15 * 60 * 1000);

    return () => {
      clearInterval(priceInterval);
      clearInterval(fullInterval);
    };
  }, []);

  // 패널 외부 클릭 시 닫기
  useEffect(() => {
    if (!showSettings) return;
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowSettings(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showSettings]);

  async function handleLogout() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

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
          <div className="flex items-center gap-2">
            {loading ? (
              <span className="text-xs text-slate-500 animate-pulse">불러오는 중...</span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live
              </span>
            )}
            {/* 프로필 버튼 */}
            <button
              onClick={() => setShowSettings((v) => !v)}
              className="ml-1 w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors"
            >
              <User size={15} />
            </button>
          </div>
        </div>
      </header>

      {/* 설정 패널 (슬라이드 다운) */}
      {showSettings && (
        <div className="fixed inset-0 z-20 bg-black/50 backdrop-blur-sm">
          <div
            ref={panelRef}
            className="absolute top-0 left-0 right-0 max-w-lg mx-auto bg-slate-900 border-b border-slate-800 rounded-b-2xl shadow-2xl px-4 pt-4 pb-6 animate-slide-down"
          >
            {/* 패널 헤더 */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <p className="text-sm font-semibold text-slate-200">계정 설정</p>
                {userEmail && (
                  <p className="text-xs text-slate-500 mt-0.5">{userEmail}</p>
                )}
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800"
              >
                <X size={16} />
              </button>
            </div>

            {/* 증권계좌 설정 */}
            {userId && <BrokerSettings userId={userId} />}

            {/* 로그아웃 */}
            <button
              onClick={handleLogout}
              className="mt-4 w-full flex items-center justify-center gap-2 rounded-xl border border-slate-700 text-slate-400 hover:text-red-400 hover:border-red-800 py-2.5 text-sm transition-colors"
            >
              <LogOut size={15} />
              로그아웃
            </button>
          </div>
        </div>
      )}

      <div className="max-w-lg mx-auto px-4 pt-4 space-y-4">
        {loading && <DashboardSkeleton />}
        {!loading && tab === "overview" && (
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

            {/* 출금 예약 */}
            <WithdrawalReservation totalValue={portfolio.total_value + portfolio.cash} />

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

        {!loading && tab === "holdings" && <HoldingsList positions={portfolio.positions} />}
        {!loading && tab === "momentum" && <MomentumRankingCard ranking={momentum_ranking} />}
        {!loading && tab === "rebalance" && (
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

function DashboardSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* 포트폴리오 카드 */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5">
        <div className="flex items-start justify-between mb-4">
          <div className="h-3 w-28 bg-slate-800 rounded" />
          <div className="h-3 w-36 bg-slate-800 rounded" />
        </div>
        <div className="h-10 w-40 bg-slate-800 rounded mb-2" />
        <div className="h-3 w-52 bg-slate-800 rounded mb-5" />
        <div className="h-9 w-28 bg-slate-800 rounded-xl mb-4" />
        <div className="grid grid-cols-2 gap-3">
          <div className="h-16 bg-slate-800 rounded-xl" />
          <div className="h-16 bg-slate-800 rounded-xl" />
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-3 gap-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-xl bg-slate-900 border border-slate-800 p-3">
            <div className="h-2 w-12 bg-slate-800 rounded mb-2 mx-auto" />
            <div className="h-4 w-14 bg-slate-800 rounded mx-auto" />
          </div>
        ))}
      </div>

      {/* 모멘텀 Top 5 */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
        <div className="h-2 w-20 bg-slate-800 rounded mb-3" />
        <div className="flex gap-2 flex-wrap">
          {[80, 96, 88, 72, 84].map((w, i) => (
            <div key={i} className={`h-7 bg-slate-800 rounded-lg`} style={{ width: `${w}px` }} />
          ))}
        </div>
      </div>

      {/* 출금 예약 */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
        <div className="h-2 w-16 bg-slate-800 rounded mb-2" />
        <div className="h-3 w-48 bg-slate-800 rounded" />
      </div>
    </div>
  );
}

function QuickStat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-xl bg-slate-900 border border-slate-800 p-3 text-center">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-sm font-bold font-mono ${color}`}>{value}</p>
    </div>
  );
}
