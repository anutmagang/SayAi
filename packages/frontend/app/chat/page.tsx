"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "@/lib/api";

type ChatMsg = { role: "user" | "assistant" | "system"; content: string };

type RunCreated = { run_id: string; session_id: string; status: string };
type RunDetail = {
  id: string;
  status: string;
  error: string | null;
  summary: Record<string, unknown> | null;
};

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [mode, setMode] = useState<"chat" | "agent">("chat");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || busy) return;
    setErr(null);
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
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
          { role: "assistant", content: detailRun.error || "Run failed." },
        ]);
        return;
      }
      const assistant =
        (detailRun.summary?.assistant as string | undefined) || "(no reply text)";
      setMessages((m) => [...m, { role: "assistant", content: assistant }]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErr(msg);
      setMessages((m) => [...m, { role: "system", content: `Error: ${msg}` }]);
    } finally {
      setBusy(false);
    }
  }, [busy, input, mode, sessionId]);

  return (
    <main className="mx-auto flex h-[calc(100vh-4rem)] max-w-3xl flex-col gap-3 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Chat</h1>
          <p className="text-xs text-slate-500">
            Uses <code className="text-slate-400">POST /api/v1/runs</code> with{" "}
            <code className="text-slate-400">await_completion</code>. Same session = threaded
            memory.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1 text-xs text-slate-400">
            <input
              type="radio"
              name="mode"
              checked={mode === "chat"}
              onChange={() => setMode("chat")}
            />
            Chat
          </label>
          <label className="flex items-center gap-1 text-xs text-slate-400">
            <input
              type="radio"
              name="mode"
              checked={mode === "agent"}
              onChange={() => setMode("agent")}
            />
            Agent
          </label>
          <Link className="text-sm text-sky-400 underline" href="/">
            Home
          </Link>
        </div>
      </div>

      {sessionId ? (
        <p className="text-xs text-slate-600">Session: {sessionId}</p>
      ) : null}

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/50 p-4">
        {messages.length === 0 ? (
          <p className="text-sm text-slate-500">
            Log in first. Send a message — first reply may take a while while the worker runs.
          </p>
        ) : null}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={
              msg.role === "user"
                ? "ml-8 rounded-lg bg-sky-950/60 px-3 py-2 text-sm text-slate-100"
                : msg.role === "system"
                  ? "text-center text-xs text-rose-300"
                  : "mr-8 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-200"
            }
          >
            {msg.content}
          </div>
        ))}
        {busy ? <p className="text-xs text-slate-500">Thinking…</p> : null}
        <div ref={bottomRef} />
      </div>

      {err ? <p className="text-xs text-rose-400">{err}</p> : null}

      <div className="flex gap-2">
        <textarea
          className="min-h-[44px] flex-1 resize-y rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          rows={2}
          placeholder="Message… (Enter to send, Shift+Enter newline)"
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
          className="self-end rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-40"
          onClick={() => void send()}
        >
          Send
        </button>
      </div>
    </main>
  );
}
