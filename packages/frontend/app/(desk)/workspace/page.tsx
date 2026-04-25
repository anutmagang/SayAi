"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type ProjectTreeEntry = { path: string; name: string; kind: "dir" | "file" };
type ProjectChangedEntry = { status: string; path: string };
type ProjectSnapshot = {
  root: string;
  cwd: string;
  tree: ProjectTreeEntry[];
  changed: ProjectChangedEntry[];
};
type ProjectFilePreview = { path: string; size: number; truncated: boolean; content: string };

export default function WorkspacePage() {
  const [project, setProject] = useState<ProjectSnapshot | null>(null);
  const [preview, setPreview] = useState<ProjectFilePreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<"all" | "added" | "modified" | "deleted" | "untracked">("all");
  const [pathQuery, setPathQuery] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    const r = await apiFetch("/api/v1/project/snapshot?depth=2");
    if (!r.ok) {
      setErr(await r.text());
      setProject(null);
      return;
    }
    setProject((await r.json()) as ProjectSnapshot);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const loadPreview = async (path: string) => {
    setBusy(true);
    try {
      const r = await apiFetch(`/api/v1/project/file?path=${encodeURIComponent(path)}`);
      if (!r.ok) {
        setPreview({
          path,
          size: 0,
          truncated: false,
          content: await r.text(),
        });
        return;
      }
      setPreview((await r.json()) as ProjectFilePreview);
    } finally {
      setBusy(false);
    }
  };

  const changed = project?.changed ?? [];
  const tree = project?.tree ?? [];
  const changedFiltered = changed.filter((f) => {
    const ok = filter === "all" || f.status === filter;
    const q = pathQuery ? f.path.toLowerCase().includes(pathQuery.toLowerCase()) : true;
    return ok && q;
  });

  return (
    <div className="min-h-0 px-4 py-6 text-slate-100">
      <div className="mx-auto max-w-5xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold">Workspace (dev)</h1>
            <p className="mt-1 text-xs text-slate-400">
              Lokal: lihat perubahan git dan preview file di mesin tempat API jalan. Bukan inti produk
              chat — dipakai saat ngembangin/self-host.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => void load()}
              className="rounded-md border border-slate-600 px-3 py-1.5 text-xs hover:bg-slate-800"
            >
              Refresh
            </button>
            <Link href="/chat" className="rounded-md border border-slate-600 px-3 py-1.5 text-xs hover:bg-slate-800">
              Kembali ke Chat
            </Link>
          </div>
        </div>

        {err ? (
          <p className="rounded border border-rose-900/50 bg-rose-950/30 p-3 text-sm text-rose-200">{err}</p>
        ) : null}

        {project ? (
          <p className="text-[11px] text-slate-500">
            Root: <code className="text-slate-400">{project.root}</code>
          </p>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2">
          <section className="rounded-xl border border-slate-800 bg-[#0a0f1d] p-4">
            <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Changed (git)</h2>
            <div className="mb-2 mt-2 flex flex-wrap gap-1">
              {(["all", "added", "modified", "deleted", "untracked"] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
                  className={`rounded px-2 py-1 text-[10px] ${
                    filter === f ? "bg-sky-700 text-white" : "bg-slate-800 text-slate-300"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <input
              value={pathQuery}
              onChange={(e) => setPathQuery(e.target.value)}
              placeholder="Filter path..."
              className="mb-2 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs outline-none"
            />
            <ul className="max-h-80 space-y-1 overflow-y-auto text-xs">
              {changedFiltered.slice(0, 80).map((f) => (
                <li key={`${f.status}-${f.path}`}>
                  <button
                    type="button"
                    onClick={() => void loadPreview(f.path)}
                    className="w-full rounded px-2 py-1 text-left hover:bg-slate-900"
                  >
                    <span className="text-slate-500">{f.status}</span>{" "}
                    <span className="text-slate-200">{f.path}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-xl border border-slate-800 bg-[#0a0f1d] p-4">
            <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Tree (shallow)</h2>
            <ul className="mt-2 max-h-80 space-y-1 overflow-y-auto text-xs">
              {tree.slice(0, 60).map((e) => (
                <li key={e.path}>
                  <button
                    type="button"
                    disabled={e.kind === "dir"}
                    onClick={() => void loadPreview(e.path)}
                    className="w-full rounded px-2 py-1 text-left hover:bg-slate-900 disabled:opacity-50"
                  >
                    <span className="text-slate-500">{e.kind}</span> {e.path}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <section className="rounded-xl border border-slate-800 bg-[#0a0f1d] p-4">
          <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Preview</h2>
          {busy ? <p className="mt-2 text-xs text-slate-500">Loading…</p> : null}
          {preview ? (
            <pre className="mt-2 max-h-[420px] overflow-auto rounded bg-slate-950 p-3 text-[11px] text-slate-300">
              {preview.content}
            </pre>
          ) : (
            <p className="mt-2 text-xs text-slate-500">Pilih file dari daftar.</p>
          )}
        </section>
      </div>
    </div>
  );
}
