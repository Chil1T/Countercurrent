import { ReactNode } from "react";

export function SurfaceCard({
  children,
  className = "",
  tone = "default",
}: {
  children: ReactNode;
  className?: string;
  tone?: "default" | "muted" | "rail";
}) {
  const toneClass =
    tone === "muted"
      ? "bg-[var(--stitch-shell-panel-soft)]"
      : tone === "rail"
        ? "bg-[var(--stitch-shell-rail)] text-stone-100"
        : "bg-[var(--stitch-shell-panel)]";

  return (
    <div
      className={`rounded-[28px] border border-[var(--stitch-shell-border)] shadow-[var(--stitch-shell-shadow)] ${toneClass} ${className}`}
    >
      {children}
    </div>
  );
}
