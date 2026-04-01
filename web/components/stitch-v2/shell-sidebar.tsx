import Link from "next/link";

import { MaterialSymbol } from "@/components/stitch-v2/material-symbol";
import { ShellAction } from "@/components/stitch-v2/shell-action";
import { AppShellState } from "@/lib/app-shell-state";

export function ShellSidebar({
  navItems,
  courseLabel,
}: {
  navItems: AppShellState["navItems"];
  courseLabel: string;
}) {
  return (
    <aside className="hidden h-screen w-64 flex-col bg-[var(--stitch-surface-container-highest)] p-4 pt-20 md:flex xl:sticky xl:top-0 xl:self-start">
      <div className="mb-8 px-2">
        <div className="flex items-center gap-3 rounded-xl bg-[var(--stitch-surface-container-lowest)] p-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[color:var(--stitch-shell-primary-soft)]">
            <MaterialSymbol name="auto_stories" className="text-[var(--stitch-shell-primary)]" />
          </div>
          <div className="min-w-0">
            <p className="font-stitch-label text-xs font-bold uppercase tracking-widest text-[var(--stitch-shell-primary-strong)]">
              Project Workspace
            </p>
            <p className="truncate text-[10px] font-medium text-[var(--stitch-on-secondary-container)]">
              {courseLabel}
            </p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1">
        {navItems.map((item) =>
          item.enabled && item.href ? (
            <Link
              key={item.label}
              href={item.href}
              className="flex items-center gap-3 border-r-4 px-4 py-3 font-stitch-label text-xs font-bold uppercase tracking-widest transition-all first:border-[var(--stitch-shell-primary)] first:bg-[color:var(--stitch-background)]/50 first:text-[var(--stitch-shell-primary-strong)] not-first:border-transparent text-[var(--stitch-on-secondary-container)] hover:bg-[var(--stitch-surface-container-low)]"
            >
              <MaterialSymbol
                name={
                  item.step === "01"
                    ? "list_alt"
                    : item.step === "02"
                      ? "layers"
                      : item.step === "03"
                        ? "folder_open"
                        : "visibility"
                }
              />
              <span className="min-w-0">
                <span>{item.label}</span>
              </span>
            </Link>
          ) : (
            <div
              key={item.label}
              className="flex items-center gap-3 px-4 py-3 font-stitch-label text-xs font-bold uppercase tracking-widest text-stone-400"
            >
              <MaterialSymbol name="radio_button_unchecked" />
              <span className="min-w-0">{item.label}</span>
            </div>
          ),
        )}
      </nav>

      <div className="mt-auto border-t border-[color:var(--stitch-outline-variant)]/30 pt-4">
        <ShellAction
          tone="inverse"
          disabled
          className="mb-4 w-full"
          icon={<MaterialSymbol name="add" className="text-sm" />}
        >
          新增章节 即将到来
        </ShellAction>
        <div className="space-y-1">
          <ShellAction disabled icon={<MaterialSymbol name="help_outline" className="text-sm" />}>
            帮助 即将到来
          </ShellAction>
          <ShellAction disabled icon={<MaterialSymbol name="archive" className="text-sm" />}>
            归档 即将到来
          </ShellAction>
        </div>
      </div>
    </aside>
  );
}
