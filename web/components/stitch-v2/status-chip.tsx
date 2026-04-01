export function StatusChip({
  label,
  tone = "default",
}: {
  label: string;
  tone?: "default" | "accent" | "muted";
}) {
  const toneClass =
    tone === "accent"
      ? "border-[var(--stitch-shell-primary)] bg-[var(--stitch-shell-primary-soft)] text-[var(--stitch-shell-primary-strong)]"
      : tone === "muted"
        ? "border-stone-200 bg-stone-100 text-stone-500"
        : "border-stone-200 bg-white text-stone-700";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] ${toneClass}`}
    >
      {label}
    </span>
  );
}
