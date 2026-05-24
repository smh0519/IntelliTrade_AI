"use client";

import { NewsItem } from "@/lib/types";
import { X, ExternalLink, Loader2, FileText } from "lucide-react";
import { useEffect, useState } from "react";

interface Props {
  item: NewsItem;
  onClose: () => void;
}

const SENTIMENT_STYLE: Record<NewsItem["sentiment"], { dot: string; badge: string; label: string }> = {
  positive: { dot: "bg-emerald-400", badge: "bg-emerald-900/50 text-emerald-300 border-emerald-800/50", label: "호재" },
  negative: { dot: "bg-red-400",     badge: "bg-red-900/50 text-red-300 border-red-800/50",             label: "악재" },
  neutral:  { dot: "bg-amber-400",   badge: "bg-amber-900/50 text-amber-300 border-amber-800/50",       label: "중립" },
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}분 전`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}시간 전`;
  return `${Math.floor(hrs / 24)}일 전`;
}

export default function NewsDetailModal({ item, onClose }: Props) {
  const [body, setBody]       = useState<string | null>(null);
  const [finalUrl, setFinalUrl] = useState<string>(item.url);
  const [loading, setLoading] = useState(true);
  const s = SENTIMENT_STYLE[item.sentiment];

  useEffect(() => {
    if (!item.url || item.url === "#") {
      setLoading(false);
      return;
    }
    fetch(`/api/news/article?url=${encodeURIComponent(item.url)}`)
      .then((r) => r.json())
      .then((d) => {
        setBody(d.body ?? null);
        if (d.finalUrl) setFinalUrl(d.finalUrl);
      })
      .catch(() => setBody(null))
      .finally(() => setLoading(false));
  }, [item.url]);

  // ESC 닫기
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // 스크롤 잠금
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Sheet */}
      <div className="relative w-full max-w-lg mx-auto bg-slate-900 rounded-t-3xl border-t border-slate-700 px-5 pt-4 pb-10 max-h-[88vh] overflow-y-auto animate-slide-up">
        {/* Handle */}
        <div className="w-10 h-1 rounded-full bg-slate-700 mx-auto mb-5" />

        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-full bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <X size={18} />
        </button>

        {/* Meta */}
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${s.dot}`} />
          {item.ticker && (
            <span className="text-xs font-mono font-bold text-slate-300 bg-slate-800 px-2 py-0.5 rounded-md">
              {item.ticker}
            </span>
          )}
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-md border ${s.badge}`}>
            {s.label}
          </span>
          <span className="ml-auto text-xs text-slate-500 flex-shrink-0">
            {item.source} · {timeAgo(item.published_at)}
          </span>
        </div>

        {/* Headline */}
        <h2 className="text-base font-bold text-slate-100 leading-snug mb-5">
          {item.headline}
        </h2>

        {/* 본문 영역 */}
        <div className="rounded-2xl bg-slate-800/60 border border-slate-700/50 p-4 mb-4">
          <p className="text-xs text-slate-500 font-medium mb-3 flex items-center gap-1.5">
            <FileText size={12} />
            기사 본문
          </p>

          {loading ? (
            <div className="flex items-center gap-2 text-slate-400 py-4 justify-center">
              <Loader2 size={16} className="animate-spin" />
              <span className="text-sm">본문 불러오는 중...</span>
            </div>
          ) : body ? (
            <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">
              {body.slice(0, 3000)}
              {body.length > 3000 && (
                <span className="text-slate-500">
                  {"\n\n"}... 전체 내용은 원문에서 확인하세요.
                </span>
              )}
            </p>
          ) : (
            <div className="text-center py-4">
              <p className="text-sm text-slate-500 mb-2">본문을 가져올 수 없습니다.</p>
              <p className="text-xs text-slate-600">아래 원문 링크에서 직접 확인해 주세요.</p>
            </div>
          )}
        </div>

        {/* 원문 링크 */}
        {finalUrl && finalUrl !== "#" && (
          <a
            href={finalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm text-slate-300 hover:text-white transition-colors"
          >
            원문 보기
            <ExternalLink size={14} />
          </a>
        )}
      </div>
    </div>
  );
}
