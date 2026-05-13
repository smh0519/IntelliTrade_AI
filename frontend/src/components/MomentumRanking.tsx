"use client";

import { MomentumRanking } from "@/lib/types";
import { Zap } from "lucide-react";

interface Props {
  ranking: MomentumRanking[];
}

export default function MomentumRankingCard({ ranking }: Props) {
  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Zap size={14} className="text-amber-400" />
        <h2 className="text-xs text-slate-500 uppercase tracking-widest">
          모멘텀 랭킹 (63일 기준)
        </h2>
      </div>

      <div className="space-y-1.5">
        {ranking.map((item) => (
          <RankRow key={item.ticker} item={item} />
        ))}
      </div>
    </div>
  );
}

function RankRow({ item }: { item: MomentumRanking }) {
  const maxMomentum = 40;
  const barWidth = Math.min(100, (Math.abs(item.momentum_pct) / maxMomentum) * 100);
  const isPositive = item.momentum_pct >= 0;

  return (
    <div
      className={`flex items-center gap-3 rounded-xl px-3 py-2 ${
        item.in_portfolio
          ? "bg-blue-950/40 border border-blue-900/40"
          : "bg-slate-800/30"
      }`}
    >
      <span className="text-xs text-slate-500 w-5 text-center font-mono">
        {item.rank}
      </span>
      <span className="text-sm font-semibold w-12">{item.ticker}</span>

      {/* Momentum bar */}
      <div className="flex-1 bg-slate-800 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            isPositive ? "bg-emerald-500" : "bg-red-500"
          }`}
          style={{ width: `${barWidth}%` }}
        />
      </div>

      <span
        className={`text-xs font-mono w-14 text-right ${
          isPositive ? "text-emerald-400" : "text-red-400"
        }`}
      >
        {isPositive ? "+" : ""}
        {item.momentum_pct.toFixed(1)}%
      </span>

      {item.in_portfolio && (
        <span className="text-xs bg-blue-900/60 text-blue-400 px-1.5 py-0.5 rounded-md">
          보유
        </span>
      )}
    </div>
  );
}
