"use client";

import { BarChart2, List, Zap, RefreshCw, Newspaper } from "lucide-react";

type Tab = "overview" | "holdings" | "momentum" | "rebalance" | "news";

interface Props {
  active: Tab;
  onChange: (tab: Tab) => void;
}

const TABS: { id: Tab; label: string; Icon: React.ElementType }[] = [
  { id: "overview",   label: "개요",     Icon: BarChart2  },
  { id: "holdings",   label: "보유종목",  Icon: List       },
  { id: "momentum",   label: "모멘텀",   Icon: Zap        },
  { id: "rebalance",  label: "리밸런싱",  Icon: RefreshCw  },
  { id: "news",       label: "뉴스",     Icon: Newspaper  },
];

export default function BottomNav({ active, onChange }: Props) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-slate-950/95 backdrop-blur border-t border-slate-800 safe-area-pb">
      <div className="flex max-w-lg mx-auto">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={`flex-1 flex flex-col items-center gap-1 py-3 text-xs transition-colors ${
              active === id
                ? "text-blue-400"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            <Icon size={20} />
            <span>{label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
