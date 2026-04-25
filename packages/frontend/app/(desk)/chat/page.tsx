"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";

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

function ChatInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [mode, setMode] = useState<"chat" | "agent">("chat");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [lastUserInput, setLastUserInput] = useState<string>("");
  const [chatSearch, setChatSearch] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (searchParams.get("new") === "1") {
      setMessages([]);
      setSessionId(null);
      setErr(null);
      router.replace("/chat", { scroll: false });
    }
  }, [searchParams, router]);

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

  const send = useCallback(async (override?: string) => {
    const text = (override ?? input).trim();
    if (!text || busy) return;
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

  const modeLabel = useMemo(() => (mode === "agent" ? "Agent" : "Chat"), [mode]);

  const quickPrompts = [
    "Ringkas ide startup saya jadi 5 poin actionable.",
    "Bantu bikin roadmap produk 30 hari.",
    "Jelaskan bug ini dengan langkah debug bertahap.",
  ];

  const recentChats = [
    "Berita Terbaru Indonesia",
    "AI Household Startup Ideas",
    "Landing Page Perusahaan",
  ];
  const recentFiltered = recentChats.filter((t) =>
    chatSearch ? t.toLowerCase().includes(chatSearch.toLowerCase()) : true,
  );

  return (
    <div className="flex h-[calc(100vh-0px)] min-h-0 flex-col bg-[#0c0c0c] text-slate-100">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 px-4 py-2.5">
        <div className="flex items-center gap-2 text-[11px] text-slate-500">
          <span>SayAi</span>
          <span className="text-slate-600">/</span>
          <span className="text-slate-400">Chat</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select className="rounded border border-slate-700 bg-[#161616] px-2 py-1 text-xs text-slate-200 outline-none">
            <option>main</option>
          </select>
          <select className="rounded border border-slate-700 bg-[#161616] px-2 py-1 text-xs text-slate-200 outline-none">
            <option>Model: server (.env)</option>
          </select>
          <span className="rounded border border-slate-700 bg-[#161616] px-2 py-0.5 text-[10px] text-slate-400">
            {modeLabel}
          </span>
          <label className="flex cursor-pointer items-center gap-1 text-[11px] text-slate-400">
            <input type="radio" name="mode" checked={mode === "chat"} onChange={() => setMode("chat")} />
            Chat
          </label>
          <label className="flex cursor-pointer items-center gap-1 text-[11px] text-slate-400">
            <input type="radio" name="mode" checked={mode === "agent"} onChange={() => setMode("agent")} />
            Agent
          </label>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto mb-6 max-w-2xl md:mr-8 md:ml-auto">
          <input
            value={chatSearch}
            onChange={(e) => setChatSearch(e.target.value)}
            placeholder="Search chats…"
            className="w-full rounded-lg border border-slate-800 bg-[#141414] px-3 py-2 text-xs text-slate-200 outline-none placeholder:text-slate-600"
          />
          <ul className="mt-2 space-y-1">
            {recentFiltered.map((t) => (
              <li key={t}>
                <button
                  type="button"
                  className="w-full truncate rounded-md px-2 py-1.5 text-left text-xs text-slate-500 hover:bg-slate-900 hover:text-slate-300"
                >
                  {t}
                </button>
              </li>
            ))}
          </ul>
        </div>

        {messages.length === 0 ? (
          <div className="mx-auto max-w-xl text-center">
            <p className="text-lg font-medium text-slate-100">Assistant</p>
            <p className="mt-1 text-xs text-slate-500">Ready to chat</p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {quickPrompts.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setInput(p)}
                  className="rounded-full border border-slate-700 bg-[#141414] px-3 py-1.5 text-xs text-slate-300 hover:border-slate-500"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <div className="mx-auto max-w-3xl space-y-4 pb-8">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={
                msg.role === "user"
                  ? "ml-8 rounded-2xl rounded-br-sm bg-slate-800/90 px-4 py-3 text-sm"
                  : msg.role === "system"
                    ? "mx-auto max-w-lg rounded-lg border border-rose-900/40 bg-rose-950/20 px-3 py-2 text-center text-xs text-rose-200"
                    : "mr-8 rounded-2xl rounded-bl-sm border border-slate-800 bg-[#141414] px-4 py-3 text-sm"
              }
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.role !== "system" ? (
                <div className="mt-2 flex gap-2 text-[10px] text-slate-500">
                  <button
                    type="button"
                    className="hover:text-slate-300"
                    onClick={() => void navigator.clipboard?.writeText(msg.content)}
                  >
                    Copy
                  </button>
                  {msg.role === "assistant" ? (
                    <button
                      type="button"
                      disabled={busy || !lastUserInput}
                      className="hover:text-slate-300 disabled:opacity-40"
                      onClick={() => void send(lastUserInput)}
                    >
                      Regenerate
                    </button>
                  ) : null}
                </div>
              ) : null}
              <p className="mt-1 text-[10px] text-slate-600">
                {new Date(msg.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
            </div>
          ))}
          {busy ? (
            <div className="mr-8 inline-flex items-center gap-2 rounded-2xl border border-slate-800 bg-[#141414] px-4 py-2 text-xs text-slate-400">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-rose-500" />
              Thinking…
            </div>
          ) : null}
          <div ref={bottomRef} />
        </div>
      </div>

      <footer className="shrink-0 border-t border-slate-800/80 bg-[#111] px-4 py-3">
        {err ? (
          <div className="mx-auto mb-2 flex max-w-3xl items-center justify-between rounded-lg border border-rose-900/40 bg-rose-950/20 px-3 py-2">
            <p className="text-xs text-rose-200">{err}</p>
            <button
              type="button"
              disabled={busy || !lastUserInput}
              onClick={() => void send(lastUserInput)}
              className="text-xs text-rose-300 underline disabled:opacity-40"
            >
              Retry
            </button>
          </div>
        ) : null}
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <textarea
            ref={textareaRef}
            className="min-h-[48px] flex-1 resize-none rounded-xl border border-slate-800 bg-[#141414] px-3 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-slate-600"
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
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-rose-700 text-white hover:bg-rose-600 disabled:opacity-40"
            onClick={() => void send()}
            aria-label="Send"
          >
            {busy ? "…" : "↑"}
          </button>
        </div>
        <p className="mx-auto mt-2 max-w-3xl text-[10px] text-slate-600">
          Shift+Enter baris baru
          {sessionId ? (
            <>
              {" "}
              · session <span className="font-mono text-slate-500">{sessionId.slice(0, 8)}…</span>
            </>
          ) : null}
        </p>
      </footer>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-[50vh] items-center justify-center text-sm text-slate-500">Loading chat…</div>
      }
    >
      <ChatInner />
    </Suspense>
  );
}
