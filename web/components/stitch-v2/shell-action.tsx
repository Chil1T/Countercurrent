import Link from "next/link";
import { ReactNode } from "react";

type ShellActionProps = {
  children: ReactNode;
  icon?: ReactNode;
  href?: string | null;
  tone?: "primary" | "ghost" | "inverse";
  disabled?: boolean;
  className?: string;
};

export function ShellAction({
  children,
  icon,
  href,
  tone = "ghost",
  disabled = false,
  className = "",
}: ShellActionProps) {
  const toneClass =
    tone === "primary"
      ? "bg-[linear-gradient(135deg,#0055d4_0%,#1d6dff_100%)] text-white shadow-[0_12px_24px_rgba(0,85,212,0.24)]"
      : tone === "inverse"
        ? "bg-[var(--stitch-inverse-surface)] text-[var(--stitch-inverse-on-surface)]"
        : "bg-white/0 text-[var(--stitch-on-secondary-container)] hover:bg-[var(--stitch-surface-container-low)]";

  const sharedClassName = `inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 font-stitch-label text-[11px] font-bold uppercase tracking-[0.24em] transition ${toneClass} ${disabled ? "cursor-not-allowed opacity-70" : ""} ${className}`.trim();

  if (href && !disabled) {
    return (
      <Link href={href} className={sharedClassName}>
        {icon}
        <span>{children}</span>
      </Link>
    );
  }

  return (
    <button type="button" disabled={disabled} className={sharedClassName}>
      {icon}
      <span>{children}</span>
    </button>
  );
}
