import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function ControlSessionsPage() {
  return (
    <DeskPlaceholder
      title="Control · Sessions"
      description="Riwayat session per UI belum dipisah. Saat ini session_id dibuat per run; lihat run terbaru di Debug."
      actions={[{ href: "/debug", label: "Runs & sessions (debug)" }]}
    />
  );
}
