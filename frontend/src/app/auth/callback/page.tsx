"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createBrowserSupabaseClient } from "@/lib/supabase";

export default function AuthCallbackPage() {
  const router = useRouter();
  const supabase = createBrowserSupabaseClient();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function handleCallback() {
      // 디버그: 실제 URL 확인
      console.log("[auth/callback] href:", window.location.href);
      console.log("[auth/callback] search:", window.location.search);
      console.log("[auth/callback] hash:", window.location.hash);

      const hash = window.location.hash.substring(1);
      const params = new URLSearchParams(hash);
      const accessToken = params.get("access_token");
      const refreshToken = params.get("refresh_token");

      // ── implicit flow: 해시에 토큰이 있는 경우 ──
      if (accessToken && refreshToken) {
        const { data, error } = await supabase.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken,
        });
        if (data.session) {
          router.replace("/");
          return;
        }
        setErrorMsg(error?.message ?? "세션 설정 실패");
        setTimeout(() => router.replace("/login?error=" + encodeURIComponent(error?.message ?? "session_failed")), 2000);
        return;
      }

      // ── PKCE flow: URL에 code가 있는 경우 ──
      const code = new URLSearchParams(window.location.search).get("code");
      if (code) {
        const { data } = await supabase.auth.exchangeCodeForSession(code);
        if (data.session) {
          router.replace("/");
          return;
        }
        // PKCE 실패(iOS Safari 등) — 세션이 쿠키에 이미 있을 수 있으므로 조용히 확인
        const { data: { session } } = await supabase.auth.getSession();
        router.replace(session ? "/" : "/login");
        return;
      }

      // ── 이미 로그인된 경우 ──
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        router.replace("/");
        return;
      }

      // ── 아무 인증 데이터도 없음 ──
      router.replace("/login?error=no_auth_data");
    }

    handleCallback();
  }, [router, supabase.auth]);

  if (errorMsg) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-sm text-red-400">{errorMsg}</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center space-y-3">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-slate-400">로그인 처리 중...</p>
      </div>
    </main>
  );
}
