"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type SkillSetting = {
  id: string;
  description: string;
  parameters: Record<string, unknown>;
  enabled: boolean;
  config: Record<string, unknown>;
};

export default function SkillsPage() {
  const [items, setItems] = useState<SkillSetting[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    const r = await apiFetch("/api/v1/skills/settings");
    if (!r.ok) {
      setErr(await r.text());
      setItems(null);
      return;
    }
    setItems((await r.json()) as SkillSetting[]);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const toggle = async (skillId: string, enabled: boolean) => {
    setBusy(skillId);
    setErr(null);
    try {
      const r = await apiFetch(`/api/v1/skills/settings/${encodeURIComponent(skillId)}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      });
      if (!r.ok) {
        setErr(await r.text());
        return;
      }
      const updated = (await r.json()) as SkillSetting;
      setItems((prev) =>
        prev ? prev.map((s) => (s.id === skillId ? { ...s, ...updated } : s)) : prev,
      );
    } finally {
      setBusy(null);
    }
  };

  const reset = async (skillId: string) => {
    setBusy(skillId);
    setErr(null);
    try {
      const r = await apiFetch(`/api/v1/skills/settings/${encodeURIComponent(skillId)}`, {
        method: "DELETE",
      });
      if (!r.ok && r.status !== 204) {
        setErr(await r.text());
        return;
      }
      await load();
    } finally {
      setBusy(null);
    }
  };

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-10">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Skill manager</h1>
          <p className="mt-2 text-slate-400">
            Per-user toggles and config for built-in skills. Disabled skills are excluded from the
            agent runtime for your account.
          </p>
        </div>
        <Link className="text-sky-400 underline" href="/">
          Home
        </Link>
      </div>

      {err ? (
        <p className="rounded border border-rose-900/60 bg-rose-950/40 p-3 text-sm text-rose-200">
          {err}
        </p>
      ) : null}

      {items === null ? (
        <p className="text-slate-400">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-slate-400">No skills returned.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {items.map((s) => (
            <li
              key={s.id}
              className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="font-mono text-sm text-sky-300">{s.id}</div>
                  <p className="mt-1 text-sm text-slate-300">{s.description}</p>
                </div>
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-600"
                    checked={s.enabled}
                    disabled={busy === s.id}
                    onChange={(e) => void toggle(s.id, e.target.checked)}
                  />
                  Enabled
                </label>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded border border-slate-600 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
                  disabled={busy === s.id}
                  onClick={() => void reset(s.id)}
                >
                  Clear override
                </button>
              </div>
              {Object.keys(s.config).length > 0 ? (
                <pre className="mt-3 max-h-40 overflow-auto rounded bg-slate-950 p-2 text-xs text-slate-400">
                  {JSON.stringify(s.config, null, 2)}
                </pre>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
