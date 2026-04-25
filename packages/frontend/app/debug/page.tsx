"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type RunRow = {
  id: string;
  session_id: string;
  mode: string;
  status: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  created_at: string;
  completed_at: string | null;
};

type WfRunRow = {
  id: string;
  workflow_id: string;
  status: string;
  created_at: string;
  completed_at: string | null;
};

type RunStep = {
  id: string;
  seq: number;
  step_type: string;
  name: string;
  status: string;
  detail: Record<string, unknown> | null;
  error: string | null;
  started_at: string;
  ended_at: string | null;
};

type WfStep = RunStep & { node_id: string };

type ObsSummary = {
  window_hours: number;
  since: string;
  runs: { count: number; prompt_tokens: number; completion_tokens: number };
  workflow_runs: { count: number };
};

export default function DebugPage() {
  const [windowHours, setWindowHours] = useState(24);
  const [summary, setSummary] = useState<ObsSummary | null>(null);
  const [runs, setRuns] = useState<RunRow[] | null>(null);
  const [wfRuns, setWfRuns] = useState<WfRunRow[] | null>(null);
  const [runTrace, setRunTrace] = useState<RunStep[] | null>(null);
  const [wfTrace, setWfTrace] = useState<WfStep[] | null>(null);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [selectedWf, setSelectedWf] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setErr(null);
    const [s, r, w] = await Promise.all([
      apiFetch(`/api/v1/observability/summary?window_hours=${windowHours}`),
      apiFetch("/api/v1/runs?limit=50"),
      apiFetch("/api/v1/workflow-runs?limit=50"),
    ]);
    if (!s.ok) {
      setErr(await s.text());
      return;
    }
    if (!r.ok) {
      setErr(await r.text());
      return;
    }
    if (!w.ok) {
      setErr(await w.text());
      return;
    }
    setSummary((await s.json()) as ObsSummary);
    setRuns((await r.json()) as RunRow[]);
    setWfRuns((await w.json()) as WfRunRow[]);
  }, [windowHours]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const openRun = async (id: string) => {
    setSelectedRun(id);
    setSelectedWf(null);
    setWfTrace(null);
    setRunTrace(null);
    const tr = await apiFetch(`/api/v1/runs/${id}/trace`);
    if (!tr.ok) {
      setErr(await tr.text());
      return;
    }
    setRunTrace((await tr.json()) as RunStep[]);
  };

  const openWf = async (id: string) => {
    setSelectedWf(id);
    setSelectedRun(null);
    setRunTrace(null);
    setWfTrace(null);
    const tr = await apiFetch(`/api/v1/workflow-runs/${id}/trace`);
    if (!tr.ok) {
      setErr(await tr.text());
      return;
    }
    setWfTrace((await tr.json()) as WfStep[]);
  };

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 p-10">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Debug & observability</h1>
          <p className="mt-2 text-slate-400">
            Token totals in a rolling window, recent runs, and step traces for your account.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-300">
            Window (h)
            <select
              className="rounded border border-slate-600 bg-slate-900 px-2 py-1"
              value={windowHours}
              onChange={(e) => setWindowHours(Number(e.target.value))}
            >
              <option value={24}>24</option>
              <option value={72}>72</option>
              <option value={168}>168</option>
            </select>
          </label>
          <button
            type="button"
            className="rounded bg-sky-700 px-3 py-1 text-sm text-white hover:bg-sky-600"
            onClick={() => void refresh()}
          >
            Refresh
          </button>
          <Link className="text-sky-400 underline" href="/">
            Home
          </Link>
        </div>
      </div>

      {err ? (
        <p className="rounded border border-rose-900/60 bg-rose-950/40 p-3 text-sm text-rose-200">
          {err}
        </p>
      ) : null}

      {summary ? (
        <section className="grid gap-3 rounded-lg border border-slate-800 bg-slate-900/40 p-4 sm:grid-cols-3">
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Runs</div>
            <div className="text-2xl font-semibold">{summary.runs.count}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Prompt tokens</div>
            <div className="text-2xl font-semibold">{summary.runs.prompt_tokens}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Completion tokens</div>
            <div className="text-2xl font-semibold">{summary.runs.completion_tokens}</div>
          </div>
          <div className="sm:col-span-3">
            <div className="text-xs uppercase tracking-wide text-slate-500">Workflow runs</div>
            <div className="text-xl font-semibold">{summary.workflow_runs.count}</div>
            <div className="mt-1 text-xs text-slate-500">Since {summary.since}</div>
          </div>
        </section>
      ) : (
        <p className="text-slate-400">Loading summary…</p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-2 text-lg font-medium text-slate-200">Agent / chat runs</h2>
          <div className="max-h-72 overflow-auto rounded border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-900 text-xs text-slate-500">
                <tr>
                  <th className="p-2">Status</th>
                  <th className="p-2">Mode</th>
                  <th className="p-2">Tokens</th>
                  <th className="p-2">When</th>
                </tr>
              </thead>
              <tbody>
                {(runs || []).map((row) => (
                  <tr
                    key={row.id}
                    className={`cursor-pointer border-t border-slate-800 hover:bg-slate-800/60 ${
                      selectedRun === row.id ? "bg-slate-800/80" : ""
                    }`}
                    onClick={() => void openRun(row.id)}
                  >
                    <td className="p-2 font-mono text-xs">{row.status}</td>
                    <td className="p-2">{row.mode}</td>
                    <td className="p-2 text-xs">
                      {row.prompt_tokens}+{row.completion_tokens}
                    </td>
                    <td className="p-2 text-xs text-slate-500">
                      {new Date(row.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="mb-2 text-lg font-medium text-slate-200">Workflow runs</h2>
          <div className="max-h-72 overflow-auto rounded border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-900 text-xs text-slate-500">
                <tr>
                  <th className="p-2">Status</th>
                  <th className="p-2">Workflow</th>
                  <th className="p-2">When</th>
                </tr>
              </thead>
              <tbody>
                {(wfRuns || []).map((row) => (
                  <tr
                    key={row.id}
                    className={`cursor-pointer border-t border-slate-800 hover:bg-slate-800/60 ${
                      selectedWf === row.id ? "bg-slate-800/80" : ""
                    }`}
                    onClick={() => void openWf(row.id)}
                  >
                    <td className="p-2 font-mono text-xs">{row.status}</td>
                    <td className="p-2 font-mono text-xs">{row.workflow_id.slice(0, 8)}…</td>
                    <td className="p-2 text-xs text-slate-500">
                      {new Date(row.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section>
        <h2 className="mb-2 text-lg font-medium text-slate-200">Trace</h2>
        {runTrace ? (
          <ol className="list-decimal space-y-2 pl-5 text-sm">
            {runTrace.map((st) => (
              <li key={st.id} className="rounded border border-slate-800 bg-slate-900/40 p-2">
                <div className="font-mono text-sky-300">
                  #{st.seq} {st.step_type} · {st.name}
                </div>
                <div className="text-xs text-slate-500">{st.status}</div>
                {st.error ? <div className="text-xs text-rose-300">{st.error}</div> : null}
                {st.detail ? (
                  <pre className="mt-1 max-h-32 overflow-auto text-xs text-slate-400">
                    {JSON.stringify(st.detail, null, 2)}
                  </pre>
                ) : null}
              </li>
            ))}
          </ol>
        ) : null}
        {wfTrace ? (
          <ol className="list-decimal space-y-2 pl-5 text-sm">
            {wfTrace.map((st) => (
              <li key={st.id} className="rounded border border-slate-800 bg-slate-900/40 p-2">
                <div className="font-mono text-sky-300">
                  #{st.seq} {st.node_id} · {st.step_type}
                </div>
                <div className="text-xs text-slate-500">{st.status}</div>
                {st.error ? <div className="text-xs text-rose-300">{st.error}</div> : null}
                {st.detail ? (
                  <pre className="mt-1 max-h-32 overflow-auto text-xs text-slate-400">
                    {JSON.stringify(st.detail, null, 2)}
                  </pre>
                ) : null}
              </li>
            ))}
          </ol>
        ) : null}
        {!runTrace && !wfTrace ? (
          <p className="text-slate-500">Select a run above to load its steps.</p>
        ) : null}
      </section>
    </main>
  );
}
