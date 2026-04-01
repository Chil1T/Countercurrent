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
      ? "bg-[var(--stitch-surface-container-low)]"
      : tone === "rail"
        ? "bg-[var(--stitch-inverse-surface)] text-[var(--stitch-inverse-on-surface)]"
        : "bg-[var(--stitch-shell-panel)]";

  return (
    <div
      className={`rounded-[var(--stitch-shell-radius-xl)] border border-[var(--stitch-shell-border)] shadow-[var(--stitch-shell-shadow)] ${toneClass} ${className}`}
    >
      {children}
    </div>
  );
}
