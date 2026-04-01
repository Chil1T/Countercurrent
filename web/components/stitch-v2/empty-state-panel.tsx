import { ReactNode } from "react";

import { SurfaceCard } from "@/components/stitch-v2/surface-card";

export function EmptyStatePanel({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <SurfaceCard className="p-6 md:p-8">
      <p className="font-stitch-label text-[11px] uppercase tracking-[0.3em] text-[var(--stitch-shell-primary-strong)]">
        {eyebrow}
      </p>
      <h2 className="font-stitch-headline mt-3 text-3xl font-black tracking-[-0.04em] text-stone-900">
        {title}
      </h2>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-stone-600 md:text-base">
        {description}
      </p>
      {actions ? <div className="mt-6 flex flex-wrap gap-3">{actions}</div> : null}
    </SurfaceCard>
  );
}
