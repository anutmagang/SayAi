"use client";

import type { ReactNode } from "react";

import { DeskSidebar } from "@/components/desk/DeskSidebar";

export function DeskShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-[calc(100vh-0px)] bg-[#0c0c0c] text-slate-100">
      <DeskSidebar />
      <div className="min-h-0 min-w-0 flex-1 overflow-x-hidden">{children}</div>
    </div>
  );
}
