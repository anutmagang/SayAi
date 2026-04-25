import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function SettingsAppearancePage() {
  return (
    <DeskPlaceholder
      title="Settings · Appearance"
      description="Tema gelap workstation default. Toggle tema terpusat belum diimplementasi — bisa ditambah lewat Tailwind + localStorage."
      actions={[{ href: "/chat", label: "Chat" }]}
    />
  );
}
