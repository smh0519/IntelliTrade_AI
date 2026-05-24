"use client";

import { useState, useEffect } from "react";

interface Props {
  totalValue: number;
}

export default function WithdrawalReservation({ totalValue }: Props) {
  const [reserved, setReserved] = useState<number | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [inputMode, setInputMode] = useState<"amount" | "percent">("percent");
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/withdrawal")
      .then((r) => r.json())
      .then((d) => setReserved(d.amount ?? null))
      .catch(() => {});
  }, []);

  const computedAmount =
    inputMode === "percent"
      ? (parseFloat(inputValue) / 100) * totalValue
      : parseFloat(inputValue);

  async function handleSubmit() {
    setError("");
    const amount = computedAmount;
    if (!amount || amount <= 0 || isNaN(amount)) {
      setError("유효한 금액을 입력하세요.");
      return;
    }
    if (amount >= totalValue) {
      setError("출금 금액이 총 자산을 초과할 수 없습니다.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("/api/withdrawal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "오류가 발생했습니다.");
      } else {
        setReserved(data.amount);
        setShowModal(false);
        setInputValue("");
      }
    } catch {
      setError("서버 연결 오류");
    } finally {
      setLoading(false);
    }
  }

  async function handleCancel() {
    setLoading(true);
    try {
      await fetch("/api/withdrawal", { method: "DELETE" });
      setReserved(null);
    } catch {
      //
    } finally {
      setLoading(false);
    }
  }

  const nextFirstTradingDay = (() => {
    const d = new Date();
    d.setMonth(d.getMonth() + 1, 1);
    while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
    return d.toLocaleDateString("ko-KR", { month: "long", day: "numeric" });
  })();

  return (
    <>
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-widest">출금 예약</p>
            <p className="text-xs text-slate-600 mt-0.5">
              다음 리밸런싱({nextFirstTradingDay}) 시 현금 출금
            </p>
          </div>
          {reserved === null ? (
            <button
              onClick={() => setShowModal(true)}
              className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold transition-colors"
            >
              예약하기
            </button>
          ) : (
            <button
              onClick={handleCancel}
              disabled={loading}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 font-semibold transition-colors"
            >
              예약 취소
            </button>
          )}
        </div>

        {reserved !== null ? (
          <div className="rounded-xl bg-amber-950/30 border border-amber-800/50 p-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-amber-400 text-base">💸</span>
              <div>
                <p className="text-sm font-bold text-amber-300">
                  ${reserved.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-slate-500">
                  총 자산의 {totalValue > 0 ? ((reserved / totalValue) * 100).toFixed(1) : "—"}%
                </p>
              </div>
            </div>
            <span className="text-xs px-2 py-0.5 rounded-md bg-amber-900/60 text-amber-300 font-mono font-semibold">
              예약됨
            </span>
          </div>
        ) : (
          <p className="text-xs text-slate-600">예약된 출금 없음</p>
        )}
      </div>

      {/* 예약 모달 */}
      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm"
          onClick={(e) => e.target === e.currentTarget && setShowModal(false)}
        >
          <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-t-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold">출금 예약</h2>
              <button
                onClick={() => { setShowModal(false); setInputValue(""); setError(""); }}
                className="text-slate-400 hover:text-slate-200 text-lg"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-500">
              다음 리밸런싱({nextFirstTradingDay}) 시 해당 금액만큼 주식을 매도하고 현금으로 보유합니다.
            </p>

            {/* 입력 모드 토글 */}
            <div className="flex gap-2">
              {(["percent", "amount"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => { setInputMode(mode); setInputValue(""); }}
                  className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-colors ${
                    inputMode === mode
                      ? "bg-blue-600 text-white"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                  }`}
                >
                  {mode === "percent" ? "비율 (%)" : "금액 ($)"}
                </button>
              ))}
            </div>

            {/* 입력 필드 */}
            <div className="relative">
              <input
                type="number"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={inputMode === "percent" ? "예: 30" : "예: 500"}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 text-sm">
                {inputMode === "percent" ? "%" : "USD"}
              </span>
            </div>

            {/* 계산 결과 미리보기 */}
            {inputValue && !isNaN(computedAmount) && computedAmount > 0 && (
              <div className="rounded-xl bg-slate-800 p-3 flex justify-between text-sm">
                <span className="text-slate-400">출금 예정액</span>
                <span className="font-bold text-white">
                  ${computedAmount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            )}

            {error && <p className="text-xs text-red-400">{error}</p>}

            <button
              onClick={handleSubmit}
              disabled={loading || !inputValue}
              className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-bold text-sm transition-colors"
            >
              {loading ? "처리 중..." : "예약 확정"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
