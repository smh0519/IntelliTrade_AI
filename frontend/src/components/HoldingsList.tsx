"use client";

import { Position } from "@/lib/types";

interface Props {
  positions: Position[];
}

export default function HoldingsList({ positions }: Props) {
  const sorted = [...positions].sort((a, b) => b.value - a.value);

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5">
      <h2 className="text-xs text-slate-500 uppercase tracking-widest mb-4">
        보유 종목
      </h2>

      <div className="space-y-2">
        {sorted.map((pos) => (
          <HoldingRow key={pos.ticker} pos={pos} />
        ))}
      </div>
    </div>
  );
}

function HoldingRow({ pos }: { pos: Position }) {
  const isPositive = pos.pnl_pct >= 0;

  return (
    <div className="flex items-center justify-between py-2.5 border-b border-slate-800/60 last:border-0">
      <div className="flex items-center gap-3 min-w-0">
        {/* Weight bar */}
        <div className="w-1.5 rounded-full bg-slate-800 h-8 flex-shrink-0 overflow-hidden">
          <div
            className={`w-full rounded-full transition-all ${
              isPositive ? "bg-emerald-500" : "bg-red-500"
            }`}
            style={{ height: `${Math.min(100, pos.weight * 5)}%` }}
          />
        </div>

        <div className="min-w-0">
          <p className="text-sm font-semibold">{pos.ticker}</p>
          <p className="text-xs text-slate-500">
            {pos.qty.toFixed(4)}주 · 평단 ${pos.avg_price.toFixed(2)}
          </p>
        </div>
      </div>

      <div className="text-right flex-shrink-0 ml-2">
        <p className="text-sm font-semibold">${pos.value.toFixed(2)}</p>
        <p
          className={`text-xs font-medium ${
            isPositive ? "text-emerald-400" : "text-red-400"
          }`}
        >
          {isPositive ? "+" : ""}
          {pos.pnl_pct.toFixed(2)}%
          <span className="text-slate-500 font-normal ml-1">{pos.weight.toFixed(1)}%</span>
        </p>
      </div>
    </div>
  );
}
