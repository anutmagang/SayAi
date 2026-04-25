import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function ControlCronPage() {
  return (
    <DeskPlaceholder
      title="Control · Cron jobs"
      description="Penjadwalan job belum built-in. Gunakan cron host atau orkestrator (K8s CronJob) untuk memanggil API atau skrip."
      actions={[{ href: "/chat", label: "Chat" }]}
    />
  );
}
