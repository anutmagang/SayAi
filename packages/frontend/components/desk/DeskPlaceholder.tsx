import Link from "next/link";

function ActionLink({ href, label }: { href: string; label: string }) {
  const cls =
    "inline-block rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-sky-300 hover:border-sky-600";
  if (href.startsWith("http://") || href.startsWith("https://")) {
    return (
      <a href={href} className={cls} target="_blank" rel="noreferrer">
        {label}
      </a>
    );
  }
  return (
    <Link href={href} className={cls}>
      {label}
    </Link>
  );
}

export function DeskPlaceholder({
  title,
  description,
  actions,
}: {
  title: string;
  description: string;
  actions?: { href: string; label: string }[];
}) {
  return (
    <div className="mx-auto max-w-2xl px-4 py-8 text-slate-100">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">SayAi · self-host</p>
      <h1 className="mt-2 text-xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-3 text-sm leading-relaxed text-slate-400">{description}</p>
      {actions?.length ? (
        <ul className="mt-6 flex flex-wrap gap-2">
          {actions.map((a) => (
            <li key={`${a.href}-${a.label}`}>
              <ActionLink href={a.href} label={a.label} />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
