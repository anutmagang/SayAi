import type { ReactNode } from "react";

import { DeskShell } from "@/components/desk/DeskShell";

export default function DeskLayout({ children }: { children: ReactNode }) {
  return <DeskShell>{children}</DeskShell>;
}
