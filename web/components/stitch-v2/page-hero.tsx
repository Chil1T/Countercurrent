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
    <SurfaceCard className="mb-6 overflow-hidden bg-[linear-gradient(135deg,rgba(255,255,255,0.96),rgba(244,239,229,0.92))] p-5 md:p-6 lg:p-7">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="font-stitch-label text-[11px] uppercase tracking-[0.34em] text-[var(--stitch-shell-primary-strong)]">
            {eyebrow}
          </p>
          <h1 className="font-stitch-headline mt-3 max-w-3xl text-3xl font-black tracking-[-0.04em] text-stone-900 md:text-4xl xl:text-5xl">
            {title}
          </h1>
          {children ? (
            <div className="mt-4 max-w-3xl text-sm leading-7 text-stone-600 md:text-base">
              {children}
            </div>
          ) : null}
        </div>
        {meta ? <div className="min-w-0 lg:max-w-sm">{meta}</div> : null}
      </div>
    </SurfaceCard>
  );
}
