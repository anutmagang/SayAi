import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function SettingsAiPage() {
  return (
    <DeskPlaceholder
      title="Settings · AI & agents"
      description="LiteLLM: set provider keys dan DEFAULT_LLM_MODEL di environment API. Agent loop memakai tools dari registry + pack manifests."
      actions={[
        { href: "/skills", label: "Skills & tools" },
        { href: "/drafts", label: "Discovery drafts" },
      ]}
    />
  );
}
