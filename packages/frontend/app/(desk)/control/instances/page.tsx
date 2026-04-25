import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function ControlInstancesPage() {
  return (
    <DeskPlaceholder
      title="Control · Instances"
      description="Manajemen banyak replika API belum di-UI-kan. Deploy multi-replica lewat Docker/Kubernetes; health di /api/v1/health/ready."
      actions={[
        { href: "/debug", label: "Debug" },
        { href: "https://github.com/anutmagang/SayAi/tree/main/deploy/k8s", label: "K8s baseline (repo)" },
      ]}
    />
  );
}
