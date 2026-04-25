"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type Collection = {
  id: string;
  name: string;
  embedding_model: string;
  vector_size: number;
  qdrant_collection: string;
};

export default function RagPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [name, setName] = useState("Docs");
  const [title, setTitle] = useState("Note");
  const [text, setText] = useState("SayAi supports RAG via Qdrant + embeddings.");
  const [query, setQuery] = useState("What is SayAi?");
  const [log, setLog] = useState("");

  async function refresh() {
    const r = await apiFetch("/api/v1/rag/collections");
    const body = await r.json().catch(() => []);
    if (!r.ok) {
      setLog(JSON.stringify(body, null, 2));
      return;
    }
    setCollections(body);
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function createCollection() {
    setLog("");
    const r = await apiFetch("/api/v1/rag/collections", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      setLog(JSON.stringify(body, null, 2));
      return;
    }
    setLog(`Created collection ${body.id}`);
    await refresh();
  }

  async function ingestFirst() {
    setLog("");
    if (!collections[0]) {
      setLog("Create a collection first.");
      return;
    }
    const id = collections[0].id;
    const r = await apiFetch(`/api/v1/rag/collections/${id}/documents`, {
      method: "POST",
      body: JSON.stringify({ title, text }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      setLog(JSON.stringify(body, null, 2));
      return;
    }
    setLog(JSON.stringify(body, null, 2));
  }

  async function queryFirst() {
    setLog("");
    if (!collections[0]) {
      setLog("Create a collection first.");
      return;
    }
    const id = collections[0].id;
    const r = await apiFetch(`/api/v1/rag/collections/${id}/query`, {
      method: "POST",
      body: JSON.stringify({ query, answer: true }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      setLog(JSON.stringify(body, null, 2));
      return;
    }
    setLog(JSON.stringify(body, null, 2));
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-10">
      <div className="flex items-center justify-between">
        <Link className="text-sky-300 underline" href="/">
          Home
        </Link>
        <button
          className="rounded-md bg-slate-800 px-3 py-1 text-sm hover:bg-slate-700"
          type="button"
          onClick={refresh}
        >
          Refresh
        </button>
      </div>

      <h1 className="text-2xl font-semibold">RAG</h1>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Collections</h2>
        <ul className="space-y-2 text-sm text-slate-200">
          {collections.map((c) => (
            <li key={c.id} className="rounded-md border border-slate-800 bg-slate-900 p-3">
              <div className="font-medium">{c.name}</div>
              <div className="text-xs text-slate-400">{c.id}</div>
            </li>
          ))}
        </ul>
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-md border border-slate-800 bg-slate-900 px-3 py-2"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button
            className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500"
            type="button"
            onClick={createCollection}
          >
            Create
          </button>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Ingest text (first collection)</h2>
        <input
          className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="min-h-[140px] w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          className="rounded-md bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700"
          type="button"
          onClick={ingestFirst}
        >
          Upload document
        </button>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Query (first collection)</h2>
        <input
          className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          className="rounded-md bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700"
          type="button"
          onClick={queryFirst}
        >
          Query + answer
        </button>
      </section>

      <pre className="max-h-[40vh] overflow-auto rounded-md bg-slate-900 p-4 text-xs text-slate-100">
        {log || "Output"}
      </pre>
    </main>
  );
}
