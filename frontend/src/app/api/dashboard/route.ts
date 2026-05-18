import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

function getServerClient() {
  return createClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

async function fetchCurrentPrices(tickers: string[]): Promise<Record<string, number>> {
  if (tickers.length === 0) return {};
  const symbols = tickers.join(",");
  const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${symbols}&fields=regularMarketPrice,preMarketPrice,postMarketPrice`;

  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0" },
      next: { revalidate: 60 },
    });
    if (!res.ok) return {};

    const json = await res.json();
    const prices: Record<string, number> = {};
    for (const q of json?.quoteResponse?.result ?? []) {
      const price = q.preMarketPrice ?? q.postMarketPrice ?? q.regularMarketPrice;
      if (price) prices[q.symbol] = price;
    }
    return prices;
  } catch {
    return {};
  }
}

async function fetchEarningsDatesFromSupabase(
  tickers: string[]
): Promise<Record<string, string | null>> {
  if (tickers.length === 0) return {};
  try {
    const { data } = await getServerClient()
      .from("earnings_calendar")
      .select("ticker, earnings_date")
      .in("ticker", tickers);

    const map: Record<string, string | null> = {};
    for (const row of (data ?? []) as { ticker: string; earnings_date: string | null }[]) {
      map[row.ticker] = row.earnings_date ?? null;
    }
    return map;
  } catch {
    return {};
  }
}

const BENCHMARKS = [
  { label: "Nasdaq 100", ticker: "QQQ" },
  { label: "S&P 500",    ticker: "SPY" },
  { label: "Dow Jones",  ticker: "DIA" },
];

async function fetchBenchmarkReturns(
  inceptionDate: Date
): Promise<{ label: string; ticker: string; return_pct: number }[]> {
  const period1 = Math.floor(inceptionDate.getTime() / 1000);
  const period2 = Math.floor(Date.now() / 1000);

  const results = await Promise.all(
    BENCHMARKS.map(async ({ label, ticker }) => {
      try {
        const url = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?period1=${period1}&period2=${period2}&interval=1d`;
        const res = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" } });
        if (!res.ok) return null;

        const json = await res.json();
        const result = json?.chart?.result?.[0];
        if (!result) return null;

        const closes = (result.indicators?.quote?.[0]?.close ?? []) as (number | null)[];
        const valid = closes.filter((c): c is number => c != null);
        if (valid.length < 2) return null;

        const return_pct = ((valid[valid.length - 1] - valid[0]) / valid[0]) * 100;
        return { label, ticker, return_pct };
      } catch {
        return null;
      }
    })
  );

  return results.filter(
    (r): r is { label: string; ticker: string; return_pct: number } => r != null
  );
}

export async function GET() {
  const client = getServerClient();

  try {
    const [snapshotRes, rankingRes, rebalanceRes, inceptionRes] = await Promise.all([
      client
        .from("portfolio_snapshots")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(1)
        .single(),
      client
        .from("momentum_rankings")
        .select("rankings, created_at")
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle(),
      client
        .from("rebalance_log")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle(),
      client
        .from("portfolio_snapshots")
        .select("created_at")
        .order("created_at", { ascending: true })
        .limit(1)
        .maybeSingle(),
    ]);

    if (snapshotRes.error && snapshotRes.error.code !== "PGRST116") {
      return NextResponse.json({ error: snapshotRes.error.message }, { status: 500 });
    }

    const snapshot = snapshotRes.data ?? null;
    const tickers = snapshot ? Object.keys(snapshot.positions ?? {}) : [];

    // 포트폴리오 최초 스냅샷 날짜 기준으로 벤치마크 수익률 계산
    const inceptionDate = inceptionRes.data?.created_at
      ? new Date(inceptionRes.data.created_at)
      : new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

    const [currentPrices, earningsDates, benchmarks] = await Promise.all([
      fetchCurrentPrices(tickers),
      fetchEarningsDatesFromSupabase(tickers),
      fetchBenchmarkReturns(inceptionDate),
    ]);

    // snapshot 포지션에 실시간가 + 실적일 덮어쓰기
    if (snapshot) {
      for (const [ticker, pos] of Object.entries(
        snapshot.positions as Record<string, { current_price: number; earnings_date?: string | null }>
      )) {
        if (currentPrices[ticker]) pos.current_price = currentPrices[ticker];
        pos.earnings_date = earningsDates[ticker] ?? null;
      }
    }

    return NextResponse.json({
      snapshot,
      ranking:    rankingRes.data ?? null,
      rebalance:  rebalanceRes.data ?? null,
      benchmarks: benchmarks.length > 0 ? benchmarks : null,
    });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
