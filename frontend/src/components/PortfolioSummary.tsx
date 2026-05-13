"use client";

import { Portfolio } from "@/lib/types";
import { TrendingUp, TrendingDown, DollarSign, Clock } from "lucide-react";

interface Props {
  portfolio: Portfolio;
}

export default function PortfolioSummary({ portfolio }: Props) {
  const isPositive = portfolio.total_pnl_pct >= 0;

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-500 uppercase tracking-widest">N10-MEW 포트폴리오</span>
        <span className="text-xs text-slate-600 flex items-center gap-1">
          <Clock size={11} /> {portfolio.last_updated}
        </span>
      </div>

      <div className="mt-3 flex items-end justify-between">
        <div>
          <p className="text-3xl font-bold tracking-tight">
            ${portfolio.total_value.toFixed(2)}
          </p>
          <p className="text-sm text-slate-500 mt-0.5">
            초기자본 ${portfolio.initial_cash.toLocaleString()}
          </p>
        </div>
        <div
          className={`flex items-center gap-1.5 text-lg font-semibold px-3 py-1.5 rounded-xl ${
            isPositive
              ? "bg-emerald-950 text-emerald-400"
              : "bg-red-950 text-red-400"
          }`}
        >
          {isPositive ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
          {isPositive ? "+" : ""}
          {portfolio.total_pnl_pct.toFixed(2)}%
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <StatCard
          label="현금"
          value={`$${portfolio.cash.toFixed(2)}`}
          icon={<DollarSign size={14} />}
        />
        <StatCard
          label="보유종목"
          value={`${portfolio.positions.length}개 종목`}
          icon={<TrendingUp size={14} />}
        />
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-slate-800/50 rounded-xl p-3">
      <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-1">
        {icon}
        {label}
      </div>
      <p className="text-sm font-semibold">{value}</p>
    </div>
  );
}
