"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { apiBaseUrl, apiFetch } from "@/lib/api";

function NavSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-3">
      <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">{title}</p>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLink({
  href,
  pathname,
  children,
  external,
}: {
  href: string;
  pathname: string;
  children: ReactNode;
  external?: boolean;
}) {
  const active = !external && isActive(pathname, href);
  const cls = `block rounded-md px-2 py-1.5 text-xs ${
    active ? "bg-rose-950/55 text-rose-50" : "text-slate-300 hover:bg-slate-800/90"
  }`;
  if (external) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className={cls}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={cls}>
      {children}
    </Link>
  );
}

export function DeskSidebar() {
  const pathname = usePathname();
  const docsUrl = `${apiBaseUrl()}/docs`;
  const [skillCount, setSkillCount] = useState<{ enabled: number; total: number } | null>(null);

  useEffect(() => {
    void (async () => {
      const r = await apiFetch("/api/v1/skills/settings");
      if (!r.ok) return;
      const rows = (await r.json()) as { enabled: boolean }[];
      setSkillCount({
        total: rows.length,
        enabled: rows.filter((s) => s.enabled).length,
      });
    })();
  }, []);

  return (
    <aside className="flex w-[268px] shrink-0 flex-col border-r border-slate-800/90 bg-[#111] py-3">
      <div className="mb-3 flex items-center gap-2 px-3">
        <span className="inline-block h-2 w-2 rounded-full bg-rose-600" />
        <span className="text-sm font-semibold text-slate-100">SayAi</span>
        <span className="ml-auto text-[10px] text-slate-500">local</span>
      </div>

      <Link
        href="/chat?new=1"
        className="mx-2 mb-2 rounded-md border border-slate-700 bg-slate-900/90 px-3 py-2 text-center text-xs text-slate-200 hover:border-slate-500"
      >
        + New chat
      </Link>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
        <NavSection title="Chat">
          <NavLink href="/chat" pathname={pathname}>
            Chat
          </NavLink>
          <NavLink href="/rag" pathname={pathname}>
            Library
          </NavLink>
          <NavLink href={docsUrl} pathname={pathname} external>
            Models &amp; API
          </NavLink>
        </NavSection>

        <NavSection title="Control">
          <NavLink href="/control/overview" pathname={pathname}>
            Overview
          </NavLink>
          <NavLink href="/control/channels" pathname={pathname}>
            Channels
          </NavLink>
          <NavLink href="/control/instances" pathname={pathname}>
            Instances
          </NavLink>
          <NavLink href="/control/sessions" pathname={pathname}>
            Sessions
          </NavLink>
          <NavLink href="/control/usage" pathname={pathname}>
            Usage
          </NavLink>
          <NavLink href="/control/cron" pathname={pathname}>
            Cron jobs
          </NavLink>
          <NavLink href="/debug" pathname={pathname}>
            Runs &amp; traces
          </NavLink>
          <NavLink href="/workflows" pathname={pathname}>
            Workflows
          </NavLink>
        </NavSection>

        <NavSection title="Agent">
          <NavLink href="/agent/agents" pathname={pathname}>
            Agents
          </NavLink>
          <NavLink href="/skills" pathname={pathname}>
            Skills
            {skillCount ? (
              <span className="ml-1 text-[10px] text-slate-500">
                ({skillCount.enabled}/{skillCount.total})
              </span>
            ) : null}
          </NavLink>
          <NavLink href="/agent/nodes" pathname={pathname}>
            Nodes
          </NavLink>
          <NavLink href="/agent/dreaming" pathname={pathname}>
            Dreaming
          </NavLink>
          <NavLink href="/drafts" pathname={pathname}>
            Discovery drafts
          </NavLink>
        </NavSection>

        <NavSection title="Settings">
          <NavLink href="/settings/config" pathname={pathname}>
            Config
          </NavLink>
          <NavLink href="/settings/communications" pathname={pathname}>
            Communications
          </NavLink>
          <NavLink href="/settings/appearance" pathname={pathname}>
            Appearance
          </NavLink>
          <NavLink href="/settings/automation" pathname={pathname}>
            Automation
          </NavLink>
          <NavLink href="/settings/infrastructure" pathname={pathname}>
            Infrastructure
          </NavLink>
          <NavLink href="/settings/ai" pathname={pathname}>
            AI &amp; agents
          </NavLink>
          <NavLink href="/workspace" pathname={pathname}>
            Workspace (repo)
          </NavLink>
          <NavLink href="/login" pathname={pathname}>
            Login
          </NavLink>
          <NavLink href={docsUrl} pathname={pathname} external>
            Docs (OpenAPI)
          </NavLink>
        </NavSection>

        <p className="mt-3 px-2 text-[10px] leading-relaxed text-slate-600">
          Full source + skill packs ship with install. Perluas agent lewat <code className="text-slate-500">skill_packs</code>{" "}
          dan builtin Python handlers.
        </p>
      </div>

      <div className="mt-auto border-t border-slate-800/90 px-3 pt-3">
        <NavLink href="/" pathname={pathname}>
          ← Home
        </NavLink>
      </div>
    </aside>
  );
}
