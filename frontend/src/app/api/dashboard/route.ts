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

// avg_price 기준으로 각 종목의 실제 매수 시점을 역산 → 포트폴리오 시작일 추정
async function inferInceptionDate(
  positions: Record<string, { qty: number; avg_price: number; current_price: number }>
): Promise<Date> {
  const FALLBACK = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000); // 90일 전
  const period1 = Math.floor((Date.now() - 2 * 365 * 24 * 60 * 60 * 1000) / 1000); // 2년치
  const period2 = Math.floor(Date.now() / 1000);

  // 현재가가 avg_price보다 5% 이상 높은 종목만 사용 (상승한 종목에서만 매수일 역산 가능)
  const candidates = Object.entries(positions).filter(
    ([, p]) => p.avg_price > 0 && p.qty > 0 && p.current_price > p.avg_price * 1.05
  );

  if (candidates.length === 0) return FALLBACK;

  const purchaseDates = await Promise.all(
    candidates.map(async ([ticker, pos]) => {
      try {
        const url = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?period1=${period1}&period2=${period2}&interval=1d`;
        const res = await fetch(url, {
          headers: { "User-Agent": "Mozilla/5.0" },
          signal: AbortSignal.timeout(8000),
          next: { revalidate: 3600 },
        });
        if (!res.ok) return null;

        const json = await res.json();
        const result = json?.chart?.result?.[0];
        if (!result) return null;

        const timestamps: number[] = result.timestamp ?? [];
        const closes: (number | null)[] = result.indicators?.quote?.[0]?.close ?? [];

        // 뒤에서 앞으로 탐색 — 현재가 상승 전 마지막으로 avg_price 이하였던 날
        const threshold = pos.avg_price * 1.02;
        for (let i = timestamps.length - 1; i >= 0; i--) {
          const c = closes[i];
          if (c != null && c <= threshold) {
            return new Date(timestamps[i] * 1000);
          }
        }
        return null;
      } catch {
        return null;
      }
    })
  );

  const validDates = purchaseDates.filter((d): d is Date => d != null);
  if (validDates.length === 0) return FALLBACK;

  // 포트폴리오 시작일 = 가장 이른 추정 매수일
  const inception = new Date(Math.min(...validDates.map((d) => d.getTime())));
  console.log("[inception] 추정 포트폴리오 시작일:", inception.toISOString().slice(0, 10),
    "| 사용 종목:", candidates.map(([t]) => t).join(", "));
  return inception;
}

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
    const [snapshotRes, rankingRes, rebalanceRes] = await Promise.all([
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
    ]);

    if (snapshotRes.error && snapshotRes.error.code !== "PGRST116") {
      return NextResponse.json({ error: snapshotRes.error.message }, { status: 500 });
    }

    const snapshot = snapshotRes.data ?? null;
    const tickers = snapshot ? Object.keys(snapshot.positions ?? {}) : [];
    const positionsRaw = (snapshot?.positions ?? {}) as Record<
      string,
      { qty: number; avg_price: number; current_price: number; earnings_date?: string | null }
    >;

    // avg_price 역산으로 실제 매수 시점 추정 + 현재가/실적일 병렬 fetch
    const [inceptionDate, currentPrices, earningsDates] = await Promise.all([
      inferInceptionDate(positionsRaw),
      fetchCurrentPrices(tickers),
      fetchEarningsDatesFromSupabase(tickers),
    ]);

    const benchmarks = await fetchBenchmarkReturns(inceptionDate);

    // snapshot 포지션에 실시간가 + 실적일 덮어쓰기
    if (snapshot) {
      for (const [ticker, pos] of Object.entries(
        positionsRaw
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
