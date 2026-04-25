import { DeskPlaceholder } from "@/components/desk/DeskPlaceholder";

export default function ControlUsagePage() {
  return (
    <DeskPlaceholder
      title="Control · Usage"
      description="Agregasi token dan hitungan run tersedia lewat API observability. UI utama ada di Debug."
      actions={[{ href: "/debug", label: "Observability & usage" }]}
    />
  );
}
