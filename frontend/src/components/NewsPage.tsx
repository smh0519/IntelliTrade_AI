"use client";

import { useState, useEffect, useCallback } from "react";
import { NewsItem } from "@/lib/types";
import NewsDetailModal from "@/components/NewsDetailModal";
import { RefreshCw } from "lucide-react";

type Filter = "all" | "portfolio" | "market";

const FILTER_LABELS: { id: Filter; label: string }[] = [
  { id: "all",       label: "전체"   },
  { id: "portfolio", label: "보유종목" },
  { id: "market",    label: "시장"   },
];

const SENTIMENT_COLOR = {
  positive: "bg-emerald-400",
  negative: "bg-red-400",
  neutral:  "bg-amber-400",
};

const SENTIMENT_LABEL = {
  positive: "호재",
  negative: "악재",
  neutral:  "중립",
};

const SENTIMENT_CARD_BORDER = {
  positive: "border-emerald-900/40",
  negative: "border-red-900/40",
  neutral:  "border-slate-800",
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}분 전`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}시간 전`;
  return `${Math.floor(hrs / 24)}일 전`;
}

function NewsCardSkeleton() {
  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 animate-pulse">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-2.5 h-2.5 rounded-full bg-slate-700" />
        <div className="h-4 w-14 rounded bg-slate-700" />
        <div className="h-4 w-10 rounded bg-slate-700" />
      </div>
      <div className="space-y-2">
        <div className="h-3.5 w-full rounded bg-slate-800" />
        <div className="h-3.5 w-5/6 rounded bg-slate-800" />
      </div>
      <div className="mt-3 h-3 w-24 rounded bg-slate-800" />
    </div>
  );
}

interface NewsCardProps {
  item: NewsItem;
  onClick: () => void;
}

function NewsCard({ item, onClick }: NewsCardProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-2xl bg-slate-900 border ${SENTIMENT_CARD_BORDER[item.sentiment]} p-4 active:scale-[0.98] transition-transform`}
    >
      <div className="flex items-center gap-2 mb-2.5">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${SENTIMENT_COLOR[item.sentiment]}`} />
        {item.ticker ? (
          <span className="text-xs font-mono font-bold text-slate-300">
            {item.ticker}
          </span>
        ) : (
          <span className="text-xs text-slate-500">시장</span>
        )}
        <span className={`text-xs font-medium ml-auto ${
          item.sentiment === "positive" ? "text-emerald-400" :
          item.sentiment === "negative" ? "text-red-400" :
          "text-amber-400"
        }`}>
          {SENTIMENT_LABEL[item.sentiment]}
        </span>
      </div>

      <p className="text-sm text-slate-100 leading-snug line-clamp-3 mb-2.5">
        {item.summary_ko}
      </p>

      <div className="flex items-center gap-1.5 text-xs text-slate-500">
        <span>{item.source}</span>
        <span>·</span>
        <span>{timeAgo(item.published_at)}</span>
      </div>
    </button>
  );
}

export default function NewsPage() {
  const [news, setNews]           = useState<NewsItem[]>([]);
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter]       = useState<Filter>("all");
  const [selected, setSelected]   = useState<NewsItem | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadNews = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const res = await fetch("/api/news", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { news: data } = await res.json();
      setNews(data);
      setLastUpdated(new Date());
    } catch (e) {
      console.error("[NewsPage]", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadNews();
  }, [loadNews]);

  const filtered = news.filter((n) => {
    if (filter === "portfolio") return n.is_portfolio_related;
    if (filter === "market")    return !n.is_portfolio_related;
    return true;
  });

  const updatedText = lastUpdated
    ? lastUpdated.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      <div className="flex gap-2">
        {FILTER_LABELS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setFilter(id)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors ${
              filter === id
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            {label}
          </button>
        ))}

        {/* Refresh */}
        <button
          onClick={() => loadNews(true)}
          disabled={refreshing}
          className="ml-auto flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
          {updatedText && <span>{updatedText} 업데이트</span>}
        </button>
      </div>

      {/* News list */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <NewsCardSkeleton key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-8 text-center">
          <p className="text-slate-500 text-sm">뉴스가 없습니다.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((item) => (
            <NewsCard
              key={item.id}
              item={item}
              onClick={() => setSelected(item)}
            />
          ))}
        </div>
      )}

      {/* Detail modal */}
      {selected && (
        <NewsDetailModal item={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
