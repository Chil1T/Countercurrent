import Image from "next/image";
import Link from "next/link";
import { ReactNode } from "react";

import { ContextPanel } from "@/components/context-panel";
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
      className="min-h-screen bg-[radial-gradient(circle_at_top,_#f7f3ea,_#ece7dc_45%,_#e2ddd2_100%)] text-stone-900"
    >
      <div className="sticky top-0 z-40 border-b border-stone-200/80 bg-[#f4efe5]/92 backdrop-blur">
        <div className="mx-auto flex w-[95vw] max-w-[1920px] flex-wrap items-center gap-3 px-3 py-3 md:px-4 lg:px-5">
          <div className="mr-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-stone-500">
              ReCurr
            </p>
          </div>

          <nav className="flex min-w-0 flex-1 flex-wrap gap-3">
            {resolvedShellState.navItems.map((item) =>
              item.enabled && item.href ? (
                <Link
                  key={item.label}
                  href={item.href}
                  className="min-w-0 rounded-full border border-stone-200 bg-white px-4 py-2 text-sm font-medium text-stone-700 shadow-sm transition hover:border-stone-300 hover:bg-stone-50"
                >
                  <span className="mr-2 text-xs uppercase tracking-[0.2em] text-stone-400">
                    {item.step}
                  </span>
                  {item.label}
                </Link>
              ) : (
                <div
                  key={item.label}
                  className="min-w-0 rounded-full border border-dashed border-stone-200 bg-stone-100/80 px-4 py-2 text-sm font-medium text-stone-400"
                >
                  <span className="mr-2 text-xs uppercase tracking-[0.2em] text-stone-400">
                    {item.step}
                  </span>
                  {item.label}
                </div>
              ),
            )}
          </nav>
          <div className="ml-auto flex h-[80px] w-[80px] shrink-0 items-center justify-center overflow-hidden">
            <Image
              src="/countercurrent-logo.svg"
              alt="ReCurr logo"
              width={100}
              height={100}
              className="h-[100px] w-[100px] max-w-none shrink-0"
              priority
            />
          </div>
        </div>
      </div>

      <div className="mx-auto grid min-h-[calc(100vh-4.75rem)] w-[95vw] max-w-[1920px] gap-5 px-3 py-4 md:px-4 lg:px-5 xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start xl:py-5">
        <main className="min-w-0 rounded-[32px] border border-stone-200/80 bg-white/92 p-4 shadow-[0_24px_70px_rgba(60,42,16,0.08)] md:p-5 xl:p-6">
          <header className="mb-6 flex flex-col gap-4 rounded-[24px] border border-stone-200 bg-stone-50/80 px-4 py-4 md:px-5 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-500">
                {eyebrow}
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
                {title}
              </h2>
            </div>
            <div className="grid gap-3 text-sm text-stone-600 sm:grid-cols-2">
              <div className="min-w-0 rounded-2xl bg-white px-4 py-3 shadow-sm">
                <div className="text-xs uppercase tracking-[0.2em] text-stone-400">
                  Course
                </div>
                <div className="mt-1 truncate font-medium text-stone-800">
                  {resolvedShellState.courseLabel}
                </div>
              </div>
              <div className="min-w-0 rounded-2xl bg-white px-4 py-3 shadow-sm">
                <div className="text-xs uppercase tracking-[0.2em] text-stone-400">
                  View
                </div>
                <div className="mt-1 font-medium text-amber-700">
                  {resolvedShellState.statusLabel}
                </div>
              </div>
            </div>
          </header>

          {children}
        </main>

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
