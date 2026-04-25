"use client";

import { useState } from "react";
import Link from "next/link";
import { apiBaseUrl } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("longpassword1");
  const [message, setMessage] = useState<string | null>(null);

  async function onLogin() {
    setMessage(null);
    const r = await fetch(`${apiBaseUrl()}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      setMessage(body?.detail || `Login failed (${r.status})`);
      return;
    }
    window.localStorage.setItem("sayai_token", body.access_token);
    setMessage("Saved token to localStorage. Go to Workflows or RAG.");
  }

  return (
    <main className="mx-auto flex max-w-lg flex-col gap-4 p-10">
      <Link className="text-sky-300 underline" href="/">
        Home
      </Link>
      <h1 className="text-2xl font-semibold">Login</h1>
      <label className="flex flex-col gap-1 text-sm">
        Email
        <input
          className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Password
        <input
          type="password"
          className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      <button
        className="rounded-md bg-sky-600 px-4 py-2 font-medium text-white hover:bg-sky-500"
        onClick={onLogin}
        type="button"
      >
        Save JWT
      </button>
      {message ? <p className="text-sm text-slate-200">{message}</p> : null}
    </main>
  );
}
