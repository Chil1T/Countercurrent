export function StatusChip({
  label,
  tone = "default",
}: {
  label: string;
  tone?: "default" | "accent" | "muted";
}) {
  const toneClass =
    tone === "accent"
      ? "border-[var(--stitch-shell-primary)] bg-[var(--stitch-primary-fixed)] text-[var(--stitch-shell-primary-strong)]"
      : tone === "muted"
        ? "border-[var(--stitch-outline-variant)] bg-[var(--stitch-surface-container)] text-[var(--stitch-on-secondary-container)]"
        : "border-[var(--stitch-outline-variant)] bg-[var(--stitch-surface-container-lowest)] text-[var(--stitch-on-surface-variant)]";

  return (
    <span
      className={`inline-flex items-center rounded-xl border px-3 py-1.5 font-stitch-label text-[10px] font-bold uppercase tracking-[0.24em] ${toneClass}`}
    >
      {label}
    </span>
  );
}
