import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function AgentAgentsPage() {
  return (
    <DeskPlaceholder
      title="Agent · Agents"
      description="Multi-persona agent registry belum ada. Saat ini mode chat vs agent + skill allowlist diatur per user lewat Skill manager."
      actions={[
        { href: "/skills", label: "Skill manager" },
        { href: "/chat", label: "Chat" },
      ]}
    />
  );
}
