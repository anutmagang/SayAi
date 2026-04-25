"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiFetch } from "@/lib/api";

type ChatMsg = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  time: number;
};

type RunCreated = { run_id: string; session_id: string; status: string };
type RunDetail = {
  id: string;
  status: string;
  error: string | null;
  summary: Record<string, unknown> | null;
};

type SkillSetting = {
  id: string;
  description: string;
  enabled: boolean;
};

type Draft = {
  id: string;
  title: string;
  status: string;
  updated_at: string;
};

type SkillPack = {
  id?: string;
  name?: string;
  version?: string;
  description?: string;
};

type ProjectTreeEntry = {
  path: string;
  name: string;
  kind: "dir" | "file";
};

type ProjectChangedEntry = {
  status: string;
  path: string;
};

type ProjectSnapshot = {
  root: string;
  cwd: string;
  tree: ProjectTreeEntry[];
  changed: ProjectChangedEntry[];
};

type ProjectFilePreview = {
  path: string;
  size: number;
  truncated: boolean;
  content: string;
};

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function friendlyError(raw: string): string {
  const low = raw.toLowerCase();
  if (low.includes("rate limit") || low.includes("quota")) {
    return "Provider LLM sedang limit/kuota habis. Ganti API key, model, atau provider lalu coba lagi.";
  }
  if (low.includes("unauthorized") || low.includes("401")) {
    return "Autentikasi gagal. Coba login ulang atau cek token API.";
  }
  if (low.includes("timeout")) {
    return "Permintaan timeout. Coba ulangi sebentar lagi.";
  }
  return "Terjadi error saat memproses balasan. Coba kirim ulang pesan.";
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [mode, setMode] = useState<"chat" | "agent">("chat");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [lastUserInput, setLastUserInput] = useState<string>("");
  const [panel, setPanel] = useState<"tools" | "discovery" | "project">("tools");
  const [skills, setSkills] = useState<SkillSetting[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [packs, setPacks] = useState<SkillPack[]>([]);
  const [project, setProject] = useState<ProjectSnapshot | null>(null);
  const [projectPreview, setProjectPreview] = useState<ProjectFilePreview | null>(null);
  const [projectBusy, setProjectBusy] = useState(false);
  const [projectFilter, setProjectFilter] = useState<"all" | "added" | "modified" | "deleted" | "untracked">("all");
  const [projectQuery, setProjectQuery] = useState("");
  const [inspectPanel, setInspectPanel] = useState<"none" | "tools" | "discovery" | "project">(
    "none",
  );
  const [auxErr, setAuxErr] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    const next = Math.min(Math.max(el.scrollHeight, 48), 180);
    el.style.height = `${next}px`;
  }, [input]);

  const loadAuxiliary = useCallback(async () => {
    setAuxErr(null);
    const [skillsRes, draftsRes, packsRes, projectRes] = await Promise.all([
      apiFetch("/api/v1/skills/settings"),
      apiFetch("/api/v1/skill-drafts"),
      apiFetch("/api/v1/skill-packs"),
      apiFetch("/api/v1/project/snapshot?depth=2"),
    ]);
    if (skillsRes.ok) {
      setSkills((await skillsRes.json()) as SkillSetting[]);
    }
    if (draftsRes.ok) {
      setDrafts((await draftsRes.json()) as Draft[]);
    }
    if (packsRes.ok) {
      const raw = (await packsRes.json()) as { packs?: SkillPack[] };
      setPacks(Array.isArray(raw.packs) ? raw.packs : []);
    }
    if (projectRes.ok) {
      setProject((await projectRes.json()) as ProjectSnapshot);
    }
    if (!skillsRes.ok || !draftsRes.ok || !packsRes.ok || !projectRes.ok) {
      setAuxErr("Sebagian data tools/discovery belum bisa dimuat.");
    }
  }, []);

  useEffect(() => {
    void loadAuxiliary();
  }, [loadAuxiliary]);

  const loadFilePreview = useCallback(async (path: string) => {
    setProjectBusy(true);
    try {
      const r = await apiFetch(`/api/v1/project/file?path=${encodeURIComponent(path)}`);
      if (!r.ok) {
        const txt = await r.text();
        setProjectPreview({
          path,
          size: 0,
          truncated: false,
          content: `Preview error: ${txt || `HTTP ${r.status}`}`,
        });
        return;
      }
      setProjectPreview((await r.json()) as ProjectFilePreview);
    } finally {
      setProjectBusy(false);
    }
  }, []);

  const send = useCallback(async (override?: string) => {
    const text = (override ?? input).trim();
    if (!text || busy) {
      return;
    }
    setErr(null);
    setInput("");
    setLastUserInput(text);
    setMessages((m) => [...m, { id: makeId(), role: "user", content: text, time: Date.now() }]);
    setBusy(true);
    try {
      const body: Record<string, unknown> = {
        mode,
        message: text,
        await_completion: true,
        tools_enabled: mode === "agent",
      };
      if (sessionId) body.session_id = sessionId;

      const r = await apiFetch("/api/v1/runs", {
        method: "POST",
        body: JSON.stringify(body),
      });
      const raw = await r.json().catch(() => ({}));
      if (!r.ok) {
        const detail =
          typeof raw?.detail === "string"
            ? raw.detail
            : JSON.stringify(raw?.detail || raw);
        throw new Error(detail || `HTTP ${r.status}`);
      }
      const created = raw as RunCreated;
      if (created.session_id) setSessionId(created.session_id);

      const r2 = await apiFetch(`/api/v1/runs/${created.run_id}`);
      const detailBody = await r2.json().catch(() => ({}));
      if (!r2.ok) {
        const d =
          typeof (detailBody as { detail?: string }).detail === "string"
            ? (detailBody as { detail: string }).detail
            : JSON.stringify(detailBody);
        throw new Error(d || `HTTP ${r2.status}`);
      }
      const detailRun = detailBody as RunDetail;
      if (detailRun.status === "failed") {
        setMessages((m) => [
          ...m,
          {
            id: makeId(),
            role: "assistant",
            content: friendlyError(detailRun.error || "Run failed."),
            time: Date.now(),
          },
        ]);
        return;
      }
      const assistant =
        (detailRun.summary?.assistant as string | undefined) || "(no reply text)";
      setMessages((m) => [
        ...m,
        { id: makeId(), role: "assistant", content: assistant, time: Date.now() },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErr(friendlyError(msg));
      setMessages((m) => [
        ...m,
        {
          id: makeId(),
          role: "system",
          content: "Respons gagal diproses. Periksa provider/model lalu coba Retry.",
          time: Date.now(),
        },
      ]);
    } finally {
      setBusy(false);
    }
  }, [busy, input, mode, sessionId]);

  const modeLabel = useMemo(() => (mode === "agent" ? "Agent mode" : "Chat mode"), [mode]);

  const quickPrompts = [
    "Ringkas ide startup saya jadi 5 poin actionable.",
    "Bantu bikin roadmap produk 30 hari.",
    "Jelaskan bug ini dengan langkah debug bertahap.",
  ];
  const recentChats = [
    "New Chat",
    "Berita Terbaru Indonesia",
    "AI Household Startup Ideas",
    "Laporan Berita Tribun",
  ];
  const enabledSkills = skills.filter((s) => s.enabled);
  const draftInReview = drafts.filter((d) => d.status === "submitted");
  const changedFiles = project?.changed ?? [];
  const recentTree = project?.tree ?? [];
  const changedFilesFiltered = changedFiles.filter((f) => {
    const statusOk = projectFilter === "all" ? true : f.status === projectFilter;
    const queryOk = projectQuery
      ? f.path.toLowerCase().includes(projectQuery.toLowerCase())
      : true;
    return statusOk && queryOk;
  });

  return (
    <main className="h-[calc(100vh-4rem)] bg-[#060912] text-slate-100">
      <div className="mx-auto grid h-full max-w-[1600px] grid-cols-[270px_1fr] gap-3 px-3 py-3 md:px-4">
        <aside className="h-full flex-col rounded-2xl border border-slate-800 bg-[#0a0f1d] p-3">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold tracking-wide text-sky-300">sayai</p>
            <span className="rounded-md bg-slate-900 px-2 py-1 text-[10px] text-slate-400">chat</span>
          </div>
          <button
            type="button"
            onClick={() => {
              setMessages([]);
              setSessionId(null);
              setErr(null);
            }}
            className="mb-3 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-left text-sm text-slate-200 hover:border-sky-600"
          >
            + New Chat
          </button>
          <div className="mb-2 rounded-lg border border-slate-800 bg-slate-900/60 p-2 text-[11px] uppercase tracking-wide text-slate-500">
            CHAT
            <div className="mt-2 space-y-1 text-xs normal-case">
              <button className="w-full rounded px-2 py-1 text-left text-slate-300 hover:bg-slate-800">Chat</button>
              <button className="w-full rounded px-2 py-1 text-left text-slate-400 hover:bg-slate-800">Library</button>
              <button className="w-full rounded px-2 py-1 text-left text-slate-400 hover:bg-slate-800">Models</button>
            </div>
          </div>
          <div className="mb-2 rounded-lg border border-slate-800 bg-slate-900/60 p-2 text-[11px] uppercase tracking-wide text-slate-500">
            AGENT
            <div className="mt-2 space-y-1 text-xs normal-case">
              <Link className="block rounded px-2 py-1 text-slate-300 hover:bg-slate-800" href="/skills">
                Skills
              </Link>
              <Link className="block rounded px-2 py-1 text-slate-300 hover:bg-slate-800" href="/drafts">
                Discovery Drafts
              </Link>
              <button
                type="button"
                onClick={() => setInspectPanel("project")}
                className="w-full rounded px-2 py-1 text-left text-slate-300 hover:bg-slate-800"
              >
                Project Files ({changedFiles.length})
              </button>
            </div>
          </div>
          <div className="mb-2 text-[11px] uppercase tracking-wide text-slate-500">Recent</div>
          <input
            value={projectQuery}
            onChange={(e) => setProjectQuery(e.target.value)}
            placeholder="Search chats..."
            className="mb-2 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200 outline-none"
          />
          <div className="space-y-1 overflow-y-auto pr-1">
            {recentChats.map((item) => (
              <button
                key={item}
                type="button"
                className="w-full truncate rounded-md px-2 py-1.5 text-left text-xs text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              >
                {item}
              </button>
            ))}
          </div>
          <div className="mt-auto border-t border-slate-800 pt-3">
            <Link className="text-xs text-slate-400 hover:text-slate-200" href="/">
              Back to Home
            </Link>
          </div>
        </aside>

        <section className="relative flex min-w-0 flex-col rounded-2xl border border-slate-800 bg-[#0b1020]">
          <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
            <div className="flex items-center gap-2">
              <select className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200 outline-none">
                <option>main</option>
                <option>workspace</option>
              </select>
              <select className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200 outline-none">
                <option>claude-opus-4.6</option>
                <option>gpt-4o-mini</option>
                <option>gemini-2.5-pro</option>
              </select>
              <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[10px] text-slate-300">
                {modeLabel}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <label className="flex cursor-pointer items-center gap-1 text-xs text-slate-300">
                <input type="radio" name="mode" checked={mode === "chat"} onChange={() => setMode("chat")} />
                Chat
              </label>
              <label className="flex cursor-pointer items-center gap-1 text-xs text-slate-300">
                <input type="radio" name="mode" checked={mode === "agent"} onChange={() => setMode("agent")} />
                Agent
              </label>
              <button
                type="button"
                className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:border-sky-600"
                onClick={() => setInspectPanel((p) => (p === "tools" ? "none" : "tools"))}
              >
                Tools
              </button>
              <button
                type="button"
                className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:border-sky-600"
                onClick={() => setInspectPanel((p) => (p === "discovery" ? "none" : "discovery"))}
              >
                Discovery
              </button>
              <button
                type="button"
                className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:border-sky-600"
                onClick={() => setInspectPanel((p) => (p === "project" ? "none" : "project"))}
              >
                Project
              </button>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            {messages.length === 0 ? (
              <div className="mx-auto mt-16 max-w-2xl text-center">
                <div className="mx-auto mb-3 h-10 w-10 rounded-full bg-rose-900/40" />
                <p className="mb-2 text-xl font-semibold">Assistant</p>
                <p className="mb-6 text-sm text-slate-400">
                  Ready to chat. Type a message below or use quick prompts.
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {quickPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => setInput(prompt)}
                      className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 hover:border-sky-600 hover:text-sky-300"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="mx-auto max-w-3xl space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={
                    msg.role === "user"
                      ? "ml-12 rounded-2xl rounded-br-md bg-sky-900/40 px-4 py-3 text-sm"
                      : msg.role === "system"
                        ? "mx-auto max-w-xl rounded-lg border border-rose-900/40 bg-rose-950/20 px-3 py-2 text-center text-xs text-rose-300"
                        : "mr-12 rounded-2xl rounded-bl-md border border-slate-800 bg-slate-900/80 px-4 py-3 text-sm"
                  }
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.role !== "system" ? (
                    <div className="mt-2 flex items-center gap-2 text-[10px] text-slate-500">
                      <button
                        type="button"
                        onClick={() => void navigator.clipboard?.writeText(msg.content)}
                        className="rounded border border-slate-700 px-1.5 py-0.5 hover:text-slate-300"
                      >
                        Copy
                      </button>
                      {msg.role === "assistant" ? (
                        <button
                          type="button"
                          disabled={busy || !lastUserInput}
                          onClick={() => void send(lastUserInput)}
                          className="rounded border border-slate-700 px-1.5 py-0.5 hover:text-slate-300 disabled:opacity-50"
                        >
                          Regenerate
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                  <p className="mt-2 text-[10px] text-slate-500">
                    {new Date(msg.time).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              ))}
              {busy ? (
                <div className="mr-12 inline-flex items-center gap-2 rounded-2xl rounded-bl-md border border-slate-800 bg-slate-900 px-4 py-2 text-xs text-slate-300">
                  <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-sky-400" />
                  Thinking...
                </div>
              ) : null}
              <div ref={bottomRef} />
            </div>
          </div>

          <div className="border-t border-slate-800 bg-[#0a0f1d] px-4 py-3">
            {err ? (
              <div className="mb-3 flex items-center justify-between rounded-lg border border-rose-900/40 bg-rose-950/20 px-3 py-2">
                <p className="text-xs text-rose-300">{err}</p>
                <button
                  type="button"
                  disabled={busy || !lastUserInput}
                  onClick={() => void send(lastUserInput)}
                  className="rounded-md border border-rose-700 px-2 py-1 text-xs text-rose-200 hover:bg-rose-900/40 disabled:opacity-50"
                >
                  Retry
                </button>
              </div>
            ) : null}
            <div className="mx-auto flex max-w-3xl items-end gap-2">
              <textarea
                ref={textareaRef}
                className="min-h-[48px] flex-1 resize-none rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-sm text-slate-100 outline-none ring-sky-500/40 placeholder:text-slate-500 focus:ring"
                rows={2}
                placeholder="Message Assistant (Enter to send)"
                value={input}
                disabled={busy}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
              />
              <button
                type="button"
                disabled={busy || !input.trim()}
                className="h-[48px] rounded-xl bg-sky-600 px-5 text-sm font-medium text-white transition hover:bg-sky-500 disabled:opacity-40"
                onClick={() => void send()}
              >
                {busy ? "Sending..." : "Send"}
              </button>
            </div>
            <div className="mx-auto mt-2 flex max-w-3xl justify-between text-[10px] text-slate-500">
              <span>Shift+Enter for new line</span>
              {sessionId ? <span>Session: {sessionId}</span> : <span>No session yet</span>}
            </div>
          </div>
          {inspectPanel !== "none" ? (
            <aside className="absolute right-3 top-16 z-20 h-[calc(100%-84px)] w-[330px] overflow-y-auto rounded-xl border border-slate-700 bg-[#0a0f1d] p-3 shadow-2xl">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{inspectPanel}</p>
                <button
                  type="button"
                  className="rounded border border-slate-700 px-2 py-0.5 text-[10px] text-slate-300"
                  onClick={() => setInspectPanel("none")}
                >
                  Close
                </button>
              </div>
              {inspectPanel === "tools" ? (
                <div className="space-y-3">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">AI Tools Runtime</p>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <p className="mb-2 text-slate-300">Enabled skills ({enabledSkills.length})</p>
                    <div className="space-y-1">
                      {enabledSkills.slice(0, 10).map((s) => (
                        <div key={s.id} className="rounded bg-slate-950/60 px-2 py-1 text-[11px] text-slate-300">
                          {s.id}
                        </div>
                      ))}
                    </div>
                    <Link className="mt-2 inline-block text-[11px] text-sky-400 hover:underline" href="/skills">
                      Open Skill Manager
                    </Link>
                  </div>
                </div>
              ) : null}
              {inspectPanel === "discovery" ? (
                <div className="space-y-3">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">AI Discovery</p>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <p className="text-slate-300">Draft pipeline</p>
                    <p className="mt-1 text-[11px]">Total drafts: {drafts.length}</p>
                    <p className="text-[11px]">Submitted: {draftInReview.length}</p>
                    <Link className="mt-2 inline-block text-[11px] text-sky-400 hover:underline" href="/drafts">
                      Open Discovery Drafts
                    </Link>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <p className="text-slate-300">Skill packs ({packs.length})</p>
                    <div className="mt-2 space-y-1">
                      {packs.slice(0, 6).map((p, idx) => (
                        <div
                          key={`${p.id ?? p.name ?? "pack"}-${idx}`}
                          className="rounded bg-slate-950/60 px-2 py-1 text-[11px] text-slate-300"
                        >
                          {p.name ?? p.id ?? "Unnamed pack"} {p.version ? `v${p.version}` : ""}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : null}
              {inspectPanel === "project" ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-[11px] uppercase tracking-wide text-slate-500">Project Files</p>
                    <button
                      type="button"
                      onClick={() => void loadAuxiliary()}
                      className="rounded border border-slate-700 px-2 py-1 text-[10px] text-slate-300 hover:border-sky-600"
                    >
                      Refresh
                    </button>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-2">
                    <div className="flex flex-wrap gap-1">
                      {(["all", "added", "modified", "deleted", "untracked"] as const).map((f) => (
                        <button
                          key={f}
                          type="button"
                          onClick={() => setProjectFilter(f)}
                          className={`rounded px-2 py-1 text-[10px] ${
                            projectFilter === f
                              ? "bg-sky-700 text-white"
                              : "bg-slate-800 text-slate-300"
                          }`}
                        >
                          {f}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <p className="mb-2 text-slate-300">
                      Changed files ({changedFilesFiltered.length})
                    </p>
                    <div className="max-h-40 space-y-1 overflow-y-auto pr-1">
                      {changedFilesFiltered.slice(0, 40).map((f) => (
                        <button
                          key={`${f.status}-${f.path}`}
                          type="button"
                          onClick={() => void loadFilePreview(f.path)}
                          className="w-full rounded bg-slate-950/60 px-2 py-1 text-left hover:bg-slate-800"
                        >
                          <p className="truncate text-[10px] text-slate-200">{f.path}</p>
                          <p className="text-[10px] uppercase text-slate-500">{f.status}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <p className="mb-2 text-slate-300">Folders & files ({recentTree.length})</p>
                    <div className="max-h-40 space-y-1 overflow-y-auto pr-1">
                      {recentTree.slice(0, 30).map((entry) => (
                        <button
                          key={entry.path}
                          type="button"
                          disabled={entry.kind === "dir"}
                          onClick={() => void loadFilePreview(entry.path)}
                          className="w-full rounded bg-slate-950/60 px-2 py-1 text-left hover:bg-slate-800 disabled:opacity-60"
                        >
                          <p className="truncate text-[10px] text-slate-200">{entry.path}</p>
                          <p className="text-[10px] uppercase text-slate-500">{entry.kind}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <p className="mb-2 text-slate-300">File preview</p>
                    {projectBusy ? <p className="text-[11px] text-slate-500">Loading preview...</p> : null}
                    {projectPreview ? (
                      <pre className="max-h-48 overflow-auto rounded bg-slate-950 p-2 text-[10px] text-slate-300">
                        {projectPreview.content}
                      </pre>
                    ) : (
                      <p className="text-[11px] text-slate-500">Click file to preview content.</p>
                    )}
                  </div>
                </div>
              ) : null}
              {auxErr ? <p className="mt-3 text-[11px] text-amber-300">{auxErr}</p> : null}
            </aside>
          ) : null}
        </section>
      </div>
    </main>
  );
}
