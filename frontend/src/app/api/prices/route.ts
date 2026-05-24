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

export async function GET() {
  try {
    const { data: snapshot } = await getServerClient()
      .from("portfolio_snapshots")
      .select("positions")
      .order("created_at", { ascending: false })
      .limit(1)
      .single();

    const tickers = snapshot ? Object.keys(snapshot.positions ?? {}) : [];
    const prices = await fetchCurrentPrices(tickers);
    return NextResponse.json({ prices });
  } catch {
    return NextResponse.json({ prices: {} });
  }
}
