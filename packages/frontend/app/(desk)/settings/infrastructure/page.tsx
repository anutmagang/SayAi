import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function SettingsInfrastructurePage() {
  return (
    <DeskPlaceholder
      title="Settings · Infrastructure"
      description="Postgres, Redis, Qdrant, reverse proxy, TLS — diatur di host/Compose/K8s. README & TUTORIAL-VPS menjelaskan bootstrap."
      actions={[{ href: "/", label: "Home" }]}
    />
  );
}
