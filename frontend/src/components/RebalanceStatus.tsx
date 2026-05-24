"use client";

import { RebalanceInfo, BenchmarkReturn } from "@/lib/types";
import { RefreshCw, AlertTriangle, CheckCircle, TrendingUp } from "lucide-react";

interface Props {
  info: RebalanceInfo;
  benchmarks: BenchmarkReturn[];
  strategyReturn: number;
}

export default function RebalanceStatus({ info, benchmarks, strategyReturn }: Props) {
  const daysUntil = Math.ceil(
    (new Date(info.next_rebalance_date).getTime() - Date.now()) / 86400000
  );

  return (
    <div className="space-y-3">
      {/* 리밸런싱 카드 */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5">
        <div className="flex items-center gap-2 mb-4">
          <RefreshCw size={14} className="text-slate-400" />
          <h2 className="text-xs text-slate-500 uppercase tracking-widest">
            리밸런싱
          </h2>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-slate-800/50 rounded-xl p-3">
            <p className="text-xs text-slate-500 mb-1">마지막 리밸런싱</p>
            <p className="text-sm font-semibold">
              {info.last_rebalance_date ?? "—"}
            </p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-3">
            <p className="text-xs text-slate-500 mb-1">다음 리밸런싱</p>
            <p className="text-sm font-semibold">
              {info.next_rebalance_date}
              <span className="text-slate-500 text-xs font-normal ml-1">
                ({daysUntil}일 후)
              </span>
            </p>
          </div>
        </div>

        {info.drift_alerts.length > 0 ? (
          <div className="flex items-start gap-2 bg-amber-950/40 border border-amber-900/40 rounded-xl p-3">
            <AlertTriangle size={14} className="text-amber-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs text-amber-400 font-medium">랭킹 이탈 감지</p>
              <p className="text-xs text-slate-400 mt-0.5">
                {info.drift_alerts.join(", ")} 종목이 12위 밖으로 이탈했습니다
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 bg-emerald-950/30 border border-emerald-900/30 rounded-xl p-3">
            <CheckCircle size={14} className="text-emerald-400" />
            <p className="text-xs text-emerald-400">모든 보유 종목이 Top 12 내에 있습니다 — 정상</p>
          </div>
        )}
      </div>

      {/* 벤치마크 비교 */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={14} className="text-slate-400" />
          <h2 className="text-xs text-slate-500 uppercase tracking-widest">
            지수 비교
          </h2>
        </div>

        <div className="space-y-2">
          <BenchmarkRow
            label="N10-MEW"
            ticker="전략"
            returnPct={strategyReturn}
            highlight
          />
          {benchmarks.map((bm) => (
            <BenchmarkRow
              key={bm.ticker}
              label={bm.label}
              ticker={bm.ticker}
              returnPct={bm.return_pct}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function BenchmarkRow({
  label,
  ticker,
  returnPct,
  highlight = false,
}: {
  label: string;
  ticker: string;
  returnPct: number;
  highlight?: boolean;
}) {
  const isPositive = returnPct >= 0;
  const maxReturn = 50;
  const barWidth = Math.min(100, (Math.abs(returnPct) / maxReturn) * 100);

  return (
    <div
      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 ${
        highlight ? "bg-blue-950/40 border border-blue-900/40" : "bg-slate-800/30"
      }`}
    >
      <div className="w-20 min-w-0">
        <p className="text-xs font-semibold truncate">{highlight ? "전략" : ticker}</p>
        {!highlight && <p className="text-xs text-slate-500 truncate">{label}</p>}
      </div>

      <div className="flex-1 bg-slate-800 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full rounded-full ${
            isPositive ? "bg-emerald-500" : "bg-red-500"
          } ${highlight ? "opacity-100" : "opacity-60"}`}
          style={{ width: `${barWidth}%` }}
        />
      </div>

      <span
        className={`text-xs font-mono w-14 text-right font-semibold ${
          isPositive ? "text-emerald-400" : "text-red-400"
        }`}
      >
        {isPositive ? "+" : ""}
        {returnPct.toFixed(2)}%
      </span>
    </div>
  );
}
