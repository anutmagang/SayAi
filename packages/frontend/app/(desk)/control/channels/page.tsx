import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function ControlChannelsPage() {
  return (
    <DeskPlaceholder
      title="Control · Channels"
      description="Multi-channel (Telegram, Discord, dsb.) belum ada di core SayAi. Placeholder untuk roadmap: webhook inbound + routing ke session."
      actions={[{ href: "/chat", label: "Back to chat" }]}
    />
  );
}
