"use client";

import { useEffect, useState } from "react";
import { createBrowserSupabaseClient } from "@/lib/supabase";
import { Check, Eye, EyeOff, Loader2 } from "lucide-react";

interface FormState {
  api_key: string;
  secret_key: string;
  account_id: string;
  base_url: string;
  is_simulation_mode: boolean;
}

const EMPTY: FormState = {
  api_key: "",
  secret_key: "",
  account_id: "",
  base_url: "",
  is_simulation_mode: true,
};

export default function BrokerSettings({ userId }: { userId: string }) {
  const supabase = createBrowserSupabaseClient();
  const [form, setForm] = useState<FormState>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [showSecret, setShowSecret] = useState(false);

  useEffect(() => {
    supabase
      .from("user_broker_credentials")
      .select("*")
      .eq("user_id", userId)
      .maybeSingle()
      .then(({ data }) => {
        if (data) {
          setForm({
            api_key: data.api_key ?? "",
            secret_key: data.secret_key ?? "",
            account_id: data.account_id ?? "",
            base_url: data.base_url ?? "",
            is_simulation_mode: data.is_simulation_mode ?? true,
          });
        }
        setLoading(false);
      });
  }, [userId, supabase]);

  async function handleSave() {
    setSaving(true);
    const { error } = await supabase
      .from("user_broker_credentials")
      .upsert(
        { user_id: userId, ...form },
        { onConflict: "user_id" }
      );
    setSaving(false);
    if (!error) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 size={20} className="animate-spin text-slate-500" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs text-slate-500 uppercase tracking-widest mb-3">
          증권계좌 API 연동
        </p>
      </div>

      {/* 시뮬레이션 모드 토글 */}
      <div className="flex items-center justify-between rounded-xl bg-slate-800 border border-slate-700 px-4 py-3">
        <div>
          <p className="text-sm font-medium text-slate-200">시뮬레이션 모드</p>
          <p className="text-xs text-slate-500 mt-0.5">
            모의투자 · 실제 주문 없음
          </p>
        </div>
        <button
          onClick={() =>
            setForm((f) => ({ ...f, is_simulation_mode: !f.is_simulation_mode }))
          }
          className={`relative w-11 h-6 rounded-full transition-colors ${
            form.is_simulation_mode ? "bg-blue-500" : "bg-slate-600"
          }`}
        >
          <span
            className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
              form.is_simulation_mode ? "left-6" : "left-1"
            }`}
          />
        </button>
      </div>

      {/* 실계좌 입력 필드 (시뮬 모드 off일 때 강조) */}
      <div
        className={`space-y-3 transition-opacity ${
          form.is_simulation_mode ? "opacity-50" : "opacity-100"
        }`}
      >
        <PasswordField
          label="API Key"
          value={form.api_key}
          show={showApiKey}
          onToggle={() => setShowApiKey((v) => !v)}
          onChange={(v) => setForm((f) => ({ ...f, api_key: v }))}
          placeholder="발급받은 API Key"
        />
        <PasswordField
          label="Secret Key"
          value={form.secret_key}
          show={showSecret}
          onToggle={() => setShowSecret((v) => !v)}
          onChange={(v) => setForm((f) => ({ ...f, secret_key: v }))}
          placeholder="발급받은 Secret Key"
        />
        <InputField
          label="계좌번호"
          value={form.account_id}
          onChange={(v) => setForm((f) => ({ ...f, account_id: v }))}
          placeholder="예: 12345678-01"
        />
        <InputField
          label="API Base URL (선택)"
          value={form.base_url}
          onChange={(v) => setForm((f) => ({ ...f, base_url: v }))}
          placeholder="https://api.yourbroker.com"
        />
      </div>

      <button
        onClick={handleSave}
        disabled={saving || saved}
        className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white font-medium py-3 transition-colors"
      >
        {saving ? (
          <Loader2 size={16} className="animate-spin" />
        ) : saved ? (
          <>
            <Check size={16} />
            저장됨
          </>
        ) : (
          "저장"
        )}
      </button>
    </div>
  );
}

function PasswordField({
  label,
  value,
  show,
  onToggle,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  show: boolean;
  onToggle: () => void;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div>
      <label className="text-xs text-slate-400 mb-1 block">{label}</label>
      <div className="relative">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm px-3 py-2.5 pr-10 placeholder:text-slate-600 focus:outline-none focus:border-blue-500"
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
        >
          {show ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
      </div>
    </div>
  );
}

function InputField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div>
      <label className="text-xs text-slate-400 mb-1 block">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm px-3 py-2.5 placeholder:text-slate-600 focus:outline-none focus:border-blue-500"
      />
    </div>
  );
}
