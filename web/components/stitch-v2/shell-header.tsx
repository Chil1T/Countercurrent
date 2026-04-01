import Image from "next/image";

import { StatusChip } from "@/components/stitch-v2/status-chip";

export function ShellHeader({
  courseLabel,
  statusLabel,
}: {
  courseLabel: string;
  statusLabel: string;
}) {
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--stitch-shell-border)] bg-[color:var(--stitch-shell-backdrop)]/92 backdrop-blur-xl">
      <div className="mx-auto flex w-[95vw] max-w-[1920px] items-center justify-between gap-4 px-3 py-3 md:px-4 lg:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-2xl border border-[var(--stitch-shell-border)] bg-white shadow-sm">
            <Image
              src="/countercurrent-logo.svg"
              alt="ReCurr logo"
              width={44}
              height={44}
              className="h-11 w-11"
              priority
            />
          </div>
          <div className="min-w-0">
            <p className="font-stitch-headline text-xl font-black tracking-[-0.08em] text-[var(--stitch-shell-primary-strong)]">
              ReCurr
            </p>
            <p className="font-stitch-label text-[11px] uppercase tracking-[0.26em] text-stone-500">
              Course Production Workbench
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2">
          <StatusChip label={`Course · ${courseLabel}`} />
          <StatusChip label={`View · ${statusLabel}`} tone="accent" />
        </div>
      </div>
    </header>
  );
}
