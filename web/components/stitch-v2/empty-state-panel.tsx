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
    <SurfaceCard className="p-6 md:p-8 lg:p-10">
      <p className="font-stitch-label text-[11px] font-bold uppercase tracking-[0.3em] text-[var(--stitch-shell-primary-strong)]">
        {eyebrow}
      </p>
      <h2 className="font-stitch-headline mt-4 text-3xl font-extrabold tracking-[-0.05em] text-stone-900 md:text-4xl">
        {title}
      </h2>
      <p className="font-stitch-body mt-5 max-w-2xl text-sm leading-8 text-[var(--stitch-on-secondary-container)] md:text-base">
        {description}
      </p>
      {actions ? <div className="mt-6 flex flex-wrap gap-3">{actions}</div> : null}
    </SurfaceCard>
  );
}
