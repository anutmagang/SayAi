"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type Draft = {
  id: string;
  title: string;
  status: string;
  body: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export default function SkillDraftsPage() {
  const [items, setItems] = useState<Draft[] | null>(null);
  const [title, setTitle] = useState("");
  const [bodyJson, setBodyJson] = useState('{\n  "proposed_id": "my.skill",\n  "extends_skill_id": "sayai.echo",\n  "notes": ""\n}');
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    const r = await apiFetch("/api/v1/skill-drafts");
    if (!r.ok) {
      setErr(await r.text());
      setItems(null);
      return;
    }
    setItems((await r.json()) as Draft[]);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const create = async () => {
    setErr(null);
    let body: Record<string, unknown>;
    try {
      body = JSON.parse(bodyJson) as Record<string, unknown>;
    } catch {
      setErr("Body must be valid JSON.");
      return;
    }
    const r = await apiFetch("/api/v1/skill-drafts", {
      method: "POST",
      body: JSON.stringify({ title: title || "Untitled", body, status: "draft" }),
    });
    if (!r.ok) {
      setErr(await r.text());
      return;
    }
    setTitle("");
    await load();
  };

  const setStatus = async (id: string, status: string) => {
    const r = await apiFetch(`/api/v1/skill-drafts/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    if (!r.ok) setErr(await r.text());
    else await load();
  };

  const remove = async (id: string) => {
    const r = await apiFetch(`/api/v1/skill-drafts/${id}`, { method: "DELETE" });
    if (!r.ok && r.status !== 204) setErr(await r.text());
    else await load();
  };

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-10">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Skill discovery drafts</h1>
          <p className="mt-2 text-slate-400">
            Capture proposed skills or pack entries before they ship. Status: draft → submitted →
            archived.
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

      <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="text-sm font-medium text-slate-300">New draft</h2>
        <input
          className="mt-2 w-full rounded border border-slate-600 bg-slate-950 px-2 py-1 text-sm"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="mt-2 w-full rounded border border-slate-600 bg-slate-950 p-2 font-mono text-xs"
          rows={8}
          value={bodyJson}
          onChange={(e) => setBodyJson(e.target.value)}
        />
        <button
          type="button"
          className="mt-2 rounded bg-sky-700 px-3 py-1 text-sm text-white hover:bg-sky-600"
          onClick={() => void create()}
        >
          Create
        </button>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-medium text-slate-400">Your drafts</h2>
        {items === null ? (
          <p className="text-slate-500">Loading…</p>
        ) : items.length === 0 ? (
          <p className="text-slate-500">None yet.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {items.map((d) => (
              <li
                key={d.id}
                className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-sm"
              >
                <div className="font-medium">{d.title}</div>
                <div className="text-xs text-slate-500">
                  {d.status} · updated {new Date(d.updated_at).toLocaleString()}
                </div>
                <pre className="mt-2 max-h-32 overflow-auto text-xs text-slate-400">
                  {JSON.stringify(d.body, null, 2)}
                </pre>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded border border-slate-600 px-2 py-0.5 text-xs"
                    onClick={() => void setStatus(d.id, "submitted")}
                  >
                    Mark submitted
                  </button>
                  <button
                    type="button"
                    className="rounded border border-slate-600 px-2 py-0.5 text-xs"
                    onClick={() => void setStatus(d.id, "archived")}
                  >
                    Archive
                  </button>
                  <button
                    type="button"
                    className="rounded border border-rose-900/50 px-2 py-0.5 text-xs text-rose-200"
                    onClick={() => void remove(d.id)}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
