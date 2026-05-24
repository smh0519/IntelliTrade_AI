import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { NewsItem } from "@/lib/types";

const FALLBACK_TICKERS = ["AMD", "MRVL", "MU", "ARM", "QCOM", "ON", "CRWD", "TXN", "PANW"];

const TICKER_KO: Record<string, string> = {
  AMD:  "AMD 반도체",
  MRVL: "마벨테크놀로지",
  MU:   "마이크론",
  ARM:  "ARM홀딩스",
  QCOM: "퀄컴",
  ON:   "ON세미컨덕터",
  CRWD: "크라우드스트라이크",
  TXN:  "텍사스인스트루먼트",
  PANW: "팔로알토네트웍스",
  NVDA: "엔비디아",
  MSFT: "마이크로소프트",
  AAPL: "애플",
  AMZN: "아마존",
  META: "메타",
  GOOG: "구글",
  TSLA: "테슬라",
};

const MARKET_QUERIES = ["나스닥 기술주", "미국 반도체 주가", "AI 주식 오늘"];

interface NaverArticle {
  url: string;
  title: string;
  source: string;
}

const HEADERS = {
  "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  Accept: "text/html,application/xhtml+xml,*/*;q=0.9",
  "Accept-Language": "ko-KR,ko;q=0.9",
  Referer: "https://www.naver.com/",
};

function decodeEntities(s: string): string {
  return s
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/<mark>/g, "")
    .replace(/<\/mark>/g, "")
    .trim();
}

function parseNaverSearch(html: string): NaverArticle[] {
  const articles: NaverArticle[] = [];

  // Naver JSON: "textHref":"n.news.naver.com/..."...(press title)..."title":"article title","titleHref":
  const pattern =
    /"textHref":"(https?:\/\/n\.news\.naver\.com\/[^"]+)"([\s\S]{1,400}?)"title":"([^"]{15,150})","titleHref":/g;

  for (const m of html.matchAll(pattern)) {
    const pressMatch = m[2].match(/"title":"([^"]{1,30})"/);
    articles.push({
      url: m[1],
      title: decodeEntities(m[3]),
      source: pressMatch ? decodeEntities(pressMatch[1]) : "네이버뉴스",
    });
  }

  return articles.slice(0, 3);
}

async function fetchNaverNews(query: string): Promise<NaverArticle[]> {
  const url = `https://search.naver.com/search.naver?where=news&query=${encodeURIComponent(query)}&sort=1&pd=4`;
  try {
    const res = await fetch(url, {
      headers: HEADERS,
      signal: AbortSignal.timeout(7000),
    });
    if (!res.ok) return [];
    const html = await res.text();
    return parseNaverSearch(html);
  } catch {
    return [];
  }
}

function koreanSentiment(text: string): NewsItem["sentiment"] {
  const t = text;
  const pos = ["급등", "상승", "호재", "강세", "신고가", "매수", "수주", "계약", "흑자",
               "증가", "성장", "돌파", "기록", "확장", "랠리", "반등", "개선", "상향"];
  const neg = ["급락", "하락", "악재", "약세", "신저가", "매도", "손실", "우려", "감소",
               "하향", "부진", "실망", "경고", "위기", "규제", "제재", "충격", "붕괴"];
  const p = pos.filter((w) => t.includes(w)).length;
  const n = neg.filter((w) => t.includes(w)).length;
  if (p > n) return "positive";
  if (n > p) return "negative";
  return "neutral";
}

async function getPortfolioTickers(userId: string): Promise<string[]> {
  try {
    const serviceClient = createClient(
      process.env.SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );
    const { data } = await serviceClient
      .from("portfolio_snapshots")
      .select("positions")
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(1)
      .single();
    if (data?.positions) return Object.keys(data.positions);
  } catch {}
  return FALLBACK_TICKERS;
}

export async function GET() {
  const authClient = await createServerSupabaseClient();
  const { data: { user } } = await authClient.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  try {
    const tickers = await getPortfolioTickers(user.id);

    const tickerQueries = tickers.map((t) => ({
      ticker: t,
      query: `${TICKER_KO[t] ?? t} 주가`,
    }));

    const [tickerResults, marketResults] = await Promise.all([
      Promise.all(tickerQueries.map(({ query }) => fetchNaverNews(query))),
      Promise.all(MARKET_QUERIES.map((q) => fetchNaverNews(q))),
    ]);

    const seen = new Set<string>();
    const news: NewsItem[] = [];

    tickerResults.forEach((items, idx) => {
      const ticker = tickers[idx];
      for (const item of items.slice(0, 2)) {
        if (!seen.has(item.title)) {
          seen.add(item.title);
          news.push({
            id: `${ticker}-${item.url.slice(-16)}`,
            ticker,
            headline: item.title,
            summary_ko: item.title,
            summary_en: null,
            source: item.source,
            url: item.url,
            sentiment: koreanSentiment(item.title),
            published_at: new Date().toISOString(),
            is_portfolio_related: true,
          });
        }
      }
    });

    for (const items of marketResults) {
      for (const item of items.slice(0, 2)) {
        if (!seen.has(item.title)) {
          seen.add(item.title);
          news.push({
            id: `market-${item.url.slice(-16)}`,
            ticker: null,
            headline: item.title,
            summary_ko: item.title,
            summary_en: null,
            source: item.source,
            url: item.url,
            sentiment: koreanSentiment(item.title),
            published_at: new Date().toISOString(),
            is_portfolio_related: false,
          });
        }
      }
    }

    if (news.length === 0) {
      return NextResponse.json({ news: MOCK_NEWS });
    }

    return NextResponse.json({ news });
  } catch (e) {
    console.error("[/api/news]", e);
    return NextResponse.json({ news: MOCK_NEWS });
  }
}

const MOCK_NEWS: NewsItem[] = [
  {
    id: "m1", ticker: "AMD", headline: "AMD, 차세대 AI 가속기 MI400 발표…엔비디아 대항마로 주목",
    summary_ko: "AMD, 차세대 AI 가속기 MI400 발표…엔비디아 대항마로 주목",
    summary_en: null, source: "한국경제", url: "#", sentiment: "positive",
    published_at: new Date(Date.now() - 1 * 3600000).toISOString(), is_portfolio_related: true,
  },
  {
    id: "m2", ticker: "MU", headline: "마이크론, HBM3E 주문 사상 최대…AI 메모리 수요 급증",
    summary_ko: "마이크론, HBM3E 주문 사상 최대…AI 메모리 수요 급증",
    summary_en: null, source: "매일경제", url: "#", sentiment: "positive",
    published_at: new Date(Date.now() - 2 * 3600000).toISOString(), is_portfolio_related: true,
  },
  {
    id: "m3", ticker: "QCOM", headline: "퀄컴, 스마트폰 시장 부진으로 매출 가이던스 하향",
    summary_ko: "퀄컴, 스마트폰 시장 부진으로 매출 가이던스 하향",
    summary_en: null, source: "연합뉴스", url: "#", sentiment: "negative",
    published_at: new Date(Date.now() - 3 * 3600000).toISOString(), is_portfolio_related: true,
  },
  {
    id: "m4", ticker: null, headline: "나스닥100 사상 최고치…AI 기술주 강세 지속",
    summary_ko: "나스닥100 사상 최고치…AI 기술주 강세 지속",
    summary_en: null, source: "서울경제", url: "#", sentiment: "positive",
    published_at: new Date(Date.now() - 5 * 3600000).toISOString(), is_portfolio_related: false,
  },
  {
    id: "m5", ticker: "CRWD", headline: "크라우드스트라이크, 연방정부 보안 계약 수주…주가 급등",
    summary_ko: "크라우드스트라이크, 연방정부 보안 계약 수주…주가 급등",
    summary_en: null, source: "뉴스1", url: "#", sentiment: "positive",
    published_at: new Date(Date.now() - 6 * 3600000).toISOString(), is_portfolio_related: true,
  },
  {
    id: "m6", ticker: null, headline: "美 대중국 반도체 수출 규제 강화 예고…반도체주 약세",
    summary_ko: "美 대중국 반도체 수출 규제 강화 예고…반도체주 약세",
    summary_en: null, source: "한국경제", url: "#", sentiment: "negative",
    published_at: new Date(Date.now() - 8 * 3600000).toISOString(), is_portfolio_related: false,
  },
];
