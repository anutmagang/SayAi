import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function AgentDreamingPage() {
  return (
    <DeskPlaceholder
      title="Agent · Dreaming"
      description="Background reflection / dreaming loop belum ada di SayAi. Placeholder untuk eksperimen future (scheduled summarization, self-critique)."
      actions={[{ href: "/drafts", label: "Discovery drafts" }]}
    />
  );
}
