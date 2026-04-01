import Image from "next/image";

import { MaterialSymbol } from "@/components/stitch-v2/material-symbol";
import { ShellAction } from "@/components/stitch-v2/shell-action";
import { StatusChip } from "@/components/stitch-v2/status-chip";

export function ShellHeader({
  courseLabel,
  statusLabel,
}: {
  courseLabel: string;
  statusLabel: string;
}) {
  return (
    <header className="fixed top-0 z-50 w-full bg-[var(--stitch-background)]/80 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-full items-center justify-between gap-4 px-4 py-4 md:px-8">
        <div className="flex min-w-0 items-center gap-6">
          <div className="flex min-w-0 items-center gap-3">
            <Image
              src="/countercurrent-logo.svg"
              alt="ReCurr logo"
              width={44}
              height={44}
              className="h-8 w-auto"
              priority
            />
            <p className="font-stitch-headline text-2xl font-black tracking-tight text-[var(--stitch-shell-primary-strong)]">
              ReCurr
            </p>
          </div>

          <nav className="hidden items-center gap-8 md:flex">
            <span className="border-b-2 border-[var(--stitch-shell-primary)] pb-1 font-stitch-body text-sm font-bold text-[var(--stitch-shell-primary)]">
              Curriculum
            </span>
            <span className="font-stitch-body text-sm font-medium text-[var(--stitch-on-secondary-container)]">
              Assets
            </span>
            <span className="font-stitch-body text-sm font-medium text-[var(--stitch-on-secondary-container)]">
              Settings
            </span>
          </nav>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-4">
          <StatusChip label={`Course · ${courseLabel}`} />
          <StatusChip label={`View · ${statusLabel}`} tone="accent" />
          <div className="hidden items-center gap-2 md:flex">
            <button type="button" className="p-2 text-[var(--stitch-on-surface-variant)] transition-colors hover:text-[var(--stitch-shell-primary)]">
              <MaterialSymbol name="notifications" />
            </button>
            <button type="button" className="p-2 text-[var(--stitch-on-surface-variant)] transition-colors hover:text-[var(--stitch-shell-primary)]">
              <MaterialSymbol name="account_circle" />
            </button>
          </div>
          <ShellAction tone="primary" icon={<MaterialSymbol name="publish" className="text-base" />}>
            Publish
          </ShellAction>
        </div>
      </div>
    </header>
  );
}
