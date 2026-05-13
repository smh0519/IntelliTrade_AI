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

  const res = await fetch(url, {
    headers: { "User-Agent": "Mozilla/5.0" },
    next: { revalidate: 60 }, // 최대 60초 캐시
  });

  if (!res.ok) return {};

  const json = await res.json();
  const quotes: Record<string, number> = {};
  for (const q of json?.quoteResponse?.result ?? []) {
    // 프리/애프터마켓 우선, 없으면 정규장가
    const price =
      q.preMarketPrice ??
      q.postMarketPrice ??
      q.regularMarketPrice;
    if (price) quotes[q.symbol] = price;
  }
  return quotes;
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

    // 포지션 티커 목록 추출 → Yahoo Finance에서 실시간 현재가 조회
    const snapshot = snapshotRes.data ?? null;
    const tickers = snapshot ? Object.keys(snapshot.positions ?? {}) : [];
    const currentPrices = await fetchCurrentPrices(tickers);

    // snapshot의 current_price를 Yahoo Finance 실시간가로 덮어쓰기
    if (snapshot && Object.keys(currentPrices).length > 0) {
      for (const [ticker, pos] of Object.entries(snapshot.positions as Record<string, { current_price: number }>)) {
        if (currentPrices[ticker]) {
          pos.current_price = currentPrices[ticker];
        }
      }
    }

    return NextResponse.json({
      snapshot,
      ranking:   rankingRes.data   ?? null,
      rebalance: rebalanceRes.data ?? null,
    });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
