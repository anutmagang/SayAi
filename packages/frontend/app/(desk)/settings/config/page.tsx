import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function SettingsConfigPage() {
  return (
    <DeskPlaceholder
      title="Settings · Config"
      description="Konfigurasi server lewat .env / Compose (SECRET_KEY, DATABASE_URL, DEFAULT_LLM_MODEL, skill sandbox, Qdrant, dll.). Lihat .env.example di repo."
      actions={[{ href: "/workspace", label: "Workspace (repo files)" }]}
    />
  );
}
