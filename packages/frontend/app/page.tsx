import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-10">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">SayAi</h1>
        <p className="mt-2 text-slate-300">
          Workflows, RAG, per-user skills, and a debug console for runs, workflow steps, and token
          totals. Log in first so the UI can call the API with your JWT.
        </p>
      </div>
      <div className="flex flex-col gap-3 text-sky-300">
        <Link className="underline" href="/login">
          Login (stores JWT in localStorage)
        </Link>
        <Link className="underline" href="/chat">
          Chat (chat / agent)
        </Link>
        <Link className="underline" href="/workspace">
          Workspace (repo / git dev)
        </Link>
        <Link className="underline" href="/skills">
          Skill manager
        </Link>
        <Link className="underline" href="/debug">
          Debug & observability
        </Link>
        <Link className="underline" href="/drafts">
          Skill discovery drafts
        </Link>
        <Link className="underline" href="/workflows">
          Visual workflow builder
        </Link>
        <Link className="underline" href="/rag">
          RAG collections
        </Link>
      </div>
    </main>
  );
}
