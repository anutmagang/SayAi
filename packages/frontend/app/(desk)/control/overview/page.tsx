import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function ControlOverviewPage() {
  return (
    <DeskPlaceholder
      title="Control · Overview"
      description="Ringkasan kontrol plane belum terhubung ke dashboard terpadu. Gunakan halaman Debug untuk runs, token, dan workflow run saat ini."
      actions={[
        { href: "/debug", label: "Open runs & observability" },
        { href: "/", label: "Home" },
      ]}
    />
  );
}
