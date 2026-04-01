import { ReactNode } from "react";

import { ContextPanel } from "@/components/context-panel";
import { PageHero } from "@/components/stitch-v2/page-hero";
import { ShellHeader } from "@/components/stitch-v2/shell-header";
import { ShellSidebar } from "@/components/stitch-v2/shell-sidebar";
import { StatusChip } from "@/components/stitch-v2/status-chip";
import { SurfaceCard } from "@/components/stitch-v2/surface-card";
import { AppShellState, buildAppShellState } from "@/lib/app-shell-state";

export function AppShell({
  title,
  eyebrow,
  children,
  shellState,
  contextIds,
}: {
  title: string;
  eyebrow: string;
  children: ReactNode;
  shellState?: AppShellState;
  contextIds?: {
    draftId?: string | null;
    runId?: string | null;
    courseId?: string | null;
  };
}) {
  const resolvedShellState = shellState ?? buildAppShellState("/", new URLSearchParams());

  return (
    <div
      suppressHydrationWarning
      className="min-h-screen bg-[var(--stitch-shell-backdrop)] text-stone-900"
    >
      <ShellHeader
        courseLabel={resolvedShellState.courseLabel}
        statusLabel={resolvedShellState.statusLabel}
      />

      <div className="mx-auto grid min-h-[calc(100vh-4.75rem)] w-[95vw] max-w-[1920px] gap-5 px-3 py-4 md:px-4 lg:px-5 xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start xl:py-5">
        <div className="grid min-w-0 gap-5 xl:grid-cols-[240px_minmax(0,1fr)]">
          <ShellSidebar
            navItems={resolvedShellState.navItems}
            courseLabel={resolvedShellState.courseLabel}
          />

          <main className="min-w-0">
            <PageHero
              eyebrow={eyebrow}
              title={title}
              meta={
                <div className="grid gap-3 sm:grid-cols-2">
                  <SurfaceCard className="p-4">
                    <div className="font-stitch-label text-[11px] uppercase tracking-[0.24em] text-stone-500">
                      Course
                    </div>
                    <div className="mt-2 truncate text-sm font-semibold text-stone-900 md:text-base">
                      {resolvedShellState.courseLabel}
                    </div>
                  </SurfaceCard>
                  <SurfaceCard className="p-4">
                    <div className="font-stitch-label text-[11px] uppercase tracking-[0.24em] text-stone-500">
                      View
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <StatusChip label={resolvedShellState.statusLabel} tone="accent" />
                    </div>
                  </SurfaceCard>
                </div>
              }
            >
              以 Stitch V2 的页面骨架重建课程生产工作台，同时保持当前输入、配置、运行、结果和调试链路不改义。
            </PageHero>

            <SurfaceCard className="p-4 md:p-5 xl:p-6">{children}</SurfaceCard>
          </main>
        </div>

        <aside className="min-w-0 rounded-[28px] border border-stone-200/80 bg-[#1f1b16] p-5 text-stone-100 shadow-[0_24px_70px_rgba(20,14,8,0.35)] xl:sticky xl:top-24">
          <div className="sticky top-24">
            <ContextPanel
              draftId={contextIds?.draftId ?? null}
              runId={contextIds?.runId ?? null}
              courseId={contextIds?.courseId ?? null}
            />
          </div>
        </aside>
      </div>
    </div>
  );
}
