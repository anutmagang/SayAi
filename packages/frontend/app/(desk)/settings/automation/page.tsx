import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function SettingsAutomationPage() {
  return (
    <DeskPlaceholder
      title="Settings · Automation"
      description="Automation utama lewat Workflows (DAG). Trigger eksternal via API POST workflow runs."
      actions={[{ href: "/workflows", label: "Workflow builder" }]}
    />
  );
}
