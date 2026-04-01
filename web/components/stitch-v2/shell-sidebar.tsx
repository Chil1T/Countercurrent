import Link from "next/link";

import { AppShellState } from "@/lib/app-shell-state";

export function ShellSidebar({
  navItems,
  courseLabel,
}: {
  navItems: AppShellState["navItems"];
  courseLabel: string;
}) {
  return (
    <aside className="rounded-[30px] border border-[var(--stitch-shell-border)] bg-[var(--stitch-shell-panel-soft)] p-4 shadow-[var(--stitch-shell-shadow)] xl:sticky xl:top-24 xl:self-start">
      <div className="rounded-[22px] bg-white px-4 py-4 shadow-sm">
        <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-stone-500">
          Project Workspace
        </p>
        <p className="mt-2 truncate text-sm font-medium text-stone-800">{courseLabel}</p>
      </div>

      <nav className="mt-4 space-y-2">
        {navItems.map((item) =>
          item.enabled && item.href ? (
            <Link
              key={item.label}
              href={item.href}
              className="group flex items-start gap-3 rounded-[22px] border border-transparent bg-white/60 px-4 py-4 transition hover:border-[var(--stitch-shell-border-strong)] hover:bg-white"
            >
              <span className="font-stitch-headline text-2xl font-black tracking-[-0.08em] text-[var(--stitch-shell-primary)]/55 group-hover:text-[var(--stitch-shell-primary)]">
                {item.step}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-stone-900">{item.label}</span>
                <span className="mt-1 block text-xs uppercase tracking-[0.18em] text-stone-500">
                  {item.hint}
                </span>
              </span>
            </Link>
          ) : (
            <div
              key={item.label}
              className="flex items-start gap-3 rounded-[22px] border border-dashed border-stone-200 bg-stone-100/75 px-4 py-4 text-stone-400"
            >
              <span className="font-stitch-headline text-2xl font-black tracking-[-0.08em]">
                {item.step}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-semibold">{item.label}</span>
                <span className="mt-1 block text-xs uppercase tracking-[0.18em]">
                  {item.hint}
                </span>
              </span>
            </div>
          ),
        )}
      </nav>
    </aside>
  );
}
