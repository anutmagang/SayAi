import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function AgentNodesPage() {
  return (
    <DeskPlaceholder
      title="Agent · Nodes"
      description="Distributed worker nodes belum di-UI-kan. Eksekusi tool berjalan di proses API dengan thread pool + timeout (lihat backend settings)."
      actions={[{ href: "/debug", label: "Debug" }]}
    />
  );
}
