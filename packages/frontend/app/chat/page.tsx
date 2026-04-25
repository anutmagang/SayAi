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

  return (
    <main className="mx-auto flex h-[calc(100vh-4rem)] max-w-4xl flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-100">SayAi Chat</h1>
          <p className="text-xs text-slate-400">
            Threaded session chat + agent loop via{" "}
            <code className="text-slate-300">POST /api/v1/runs</code>.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex cursor-pointer items-center gap-1 text-xs text-slate-300">
            <input
              type="radio"
              name="mode"
              checked={mode === "chat"}
              onChange={() => setMode("chat")}
            />
            Chat
          </label>
          <label className="flex cursor-pointer items-center gap-1 text-xs text-slate-300">
            <input
              type="radio"
              name="mode"
              checked={mode === "agent"}
              onChange={() => setMode("agent")}
            />
            Agent
          </label>
          <Link className="text-sm text-sky-400 underline-offset-2 hover:underline" href="/">
            Home
          </Link>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs">
        <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-2 py-1 text-slate-300">
          {modeLabel}
        </span>
        {sessionId ? <span className="text-slate-500">Session: {sessionId}</span> : null}
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
        {messages.length === 0 ? (
          <div className="space-y-3 rounded-xl border border-dashed border-slate-700 bg-slate-900/40 p-4">
            <p className="text-sm text-slate-300">Mulai percakapan dengan prompt berikut:</p>
            <div className="flex flex-wrap gap-2">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setInput(prompt)}
                  className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-300 hover:border-sky-600 hover:text-sky-300"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={
              msg.role === "user"
                ? "ml-10 rounded-2xl rounded-br-md bg-sky-900/45 px-4 py-3 text-sm text-slate-100"
                : msg.role === "system"
                  ? "mx-auto max-w-xl rounded-lg border border-rose-900/40 bg-rose-950/20 px-3 py-2 text-center text-xs text-rose-300"
                  : "mr-10 rounded-2xl rounded-bl-md border border-slate-800 bg-slate-900/85 px-4 py-3 text-sm text-slate-100"
            }
          >
            <p className="whitespace-pre-wrap">{msg.content}</p>
            <p className="mt-2 text-[10px] text-slate-500">
              {new Date(msg.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </p>
          </div>
        ))}
        {busy ? (
          <div className="mr-10 inline-flex w-fit items-center gap-2 rounded-2xl rounded-bl-md border border-slate-800 bg-slate-900 px-4 py-2 text-xs text-slate-300">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-sky-400" />
            Thinking...
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>

      {err ? (
        <div className="flex items-center justify-between rounded-lg border border-rose-900/40 bg-rose-950/20 px-3 py-2">
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

      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          className="min-h-[48px] flex-1 resize-none rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-sm text-slate-100 outline-none ring-sky-500/40 placeholder:text-slate-500 focus:ring"
          rows={2}
          placeholder="Message... (Enter kirim, Shift+Enter baris baru)"
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
    </main>
  );
}
