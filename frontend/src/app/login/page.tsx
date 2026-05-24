"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createBrowserSupabaseClient } from "@/lib/supabase";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const errorMsg = searchParams.get("error");
  const supabase = createBrowserSupabaseClient();

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user) router.replace("/");
    });
  }, [router, supabase.auth]);

  async function handleGoogleLogin() {
    const origin = window.location.origin;
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${origin}/auth/callback` },
    });
  }

  return (
    <main className="min-h-screen bg-slate-950 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            IntelliTrade AI
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            N10-MEW 나스닥 모멘텀 퀀트 트레이딩
          </p>
        </div>

        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-8 space-y-6">
          <div className="text-center">
            <p className="text-sm text-slate-400">계정으로 로그인하세요</p>
          </div>

          {errorMsg && (
            <div className="rounded-lg bg-red-950/50 border border-red-800/50 px-3 py-2">
              <p className="text-xs text-red-400 break-all">{decodeURIComponent(errorMsg)}</p>
            </div>
          )}

          <button
            onClick={handleGoogleLogin}
            className="w-full flex items-center justify-center gap-3 rounded-xl bg-white text-slate-900 font-medium py-3 px-4 hover:bg-slate-100 transition-colors"
          >
            <GoogleIcon />
            Google로 로그인
          </button>
        </div>

        <p className="text-center text-xs text-slate-600">
          승인된 계정만 접근할 수 있습니다
        </p>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-slate-700 border-t-slate-400 rounded-full animate-spin" />
      </main>
    }>
      <LoginContent />
    </Suspense>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M17.64 9.2045c0-.6381-.0573-1.2518-.1636-1.8409H9v3.4814h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2581h2.9087c1.7018-1.5668 2.6836-3.874 2.6836-6.615z" fill="#4285F4" />
      <path d="M9 18c2.43 0 4.4673-.806 5.9564-2.1805l-2.9087-2.2581c-.8059.54-1.8368.859-3.0477.859-2.344 0-4.3282-1.5831-5.036-3.7104H.9574v2.3318C2.4382 15.9832 5.4818 18 9 18z" fill="#34A853" />
      <path d="M3.964 10.71c-.18-.54-.2822-1.1168-.2822-1.71s.1023-1.17.2823-1.71V4.9582H.9573C.3477 6.173 0 7.5482 0 9s.3477 2.827.9573 4.0418L3.964 10.71z" fill="#FBBC05" />
      <path d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.346l2.5813-2.5814C13.4627.8918 11.4255 0 9 0 5.4818 0 2.4382 2.0168.9573 4.9582L3.964 7.29C4.6718 5.1627 6.656 3.5795 9 3.5795z" fill="#EA4335" />
    </svg>
  );
}
