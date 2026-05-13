import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

// service_role 키는 서버에서만 사용 — 브라우저에 절대 노출 안됨
function getServerClient() {
  return createClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
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

    return NextResponse.json({
      snapshot:  snapshotRes.data  ?? null,
      ranking:   rankingRes.data   ?? null,
      rebalance: rebalanceRes.data ?? null,
    });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
