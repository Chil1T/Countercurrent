import { ReactNode } from "react";

import { SurfaceCard } from "@/components/stitch-v2/surface-card";

export function PageHero({
  eyebrow,
  title,
  children,
  meta,
}: {
  eyebrow: string;
  title: string;
  children?: ReactNode;
  meta?: ReactNode;
}) {
  return (
    <SurfaceCard className="mb-8 overflow-hidden bg-[var(--stitch-surface-container-lowest)] p-6 md:p-8 xl:p-10">
      <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
        <div className="min-w-0">
          <p className="font-stitch-label text-[11px] font-bold uppercase tracking-[0.28em] text-[var(--stitch-shell-primary)]">
            {eyebrow}
          </p>
          <h1 className="font-stitch-headline mt-4 max-w-3xl text-4xl font-extrabold leading-tight tracking-[-0.05em] text-stone-900 md:text-5xl xl:text-6xl">
            {title}
          </h1>
          {children ? (
            <div className="font-stitch-body mt-5 max-w-3xl text-sm leading-8 text-[var(--stitch-on-secondary-container)] md:text-base">
              {children}
            </div>
          ) : null}
        </div>
        {meta ? <div className="min-w-0 xl:max-w-sm">{meta}</div> : null}
      </div>
    </SurfaceCard>
  );
}
