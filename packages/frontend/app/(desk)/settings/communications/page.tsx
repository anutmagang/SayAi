import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function SettingsCommunicationsPage() {
  return (
    <DeskPlaceholder
      title="Settings · Communications"
      description="Webhook outbound / email belum built-in. Integrasi lewat workflow atau skill custom (HTTP GET sudah ada dengan allowlist)."
      actions={[{ href: "/skills", label: "Skills" }]}
    />
  );
}
