import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { TemplateConfigWorkbench } from "@/components/config/template-config-workbench";
import { buildAppShellState } from "@/lib/app-shell-state";

export default async function ConfigPage({
  searchParams,
}: {
  searchParams: Promise<{ draftId?: string; runId?: string; courseId?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  const shellSearchParams = new URLSearchParams();
  if (resolvedSearchParams.draftId) {
    shellSearchParams.set("draftId", resolvedSearchParams.draftId);
  }
  if (resolvedSearchParams.runId) {
    shellSearchParams.set("runId", resolvedSearchParams.runId);
  }
  if (resolvedSearchParams.courseId) {
    shellSearchParams.set("courseId", resolvedSearchParams.courseId);
  }

  return (
    <AppShell
      eyebrow="Step 2"
      title="配置页"
      shellState={buildAppShellState("/courses/new/config", shellSearchParams)}
      contextIds={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: resolvedSearchParams.runId ?? null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    >
      <Suspense
        fallback={
          <div className="rounded-[28px] border border-stone-200 bg-white p-6 text-sm text-stone-600">
            正在加载模板配置工作台...
          </div>
        }
      >
        <TemplateConfigWorkbench />
      </Suspense>
    </AppShell>
  );
}
