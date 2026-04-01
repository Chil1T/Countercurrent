import { AppShell } from "@/components/app-shell";
import { RunSessionWorkbenchV2 } from "@/components/run/run-session-workbench-v2";
import { buildAppShellState } from "@/lib/app-shell-state";
import {
  buildRunWorkbenchPreview,
  resolvePreviewScenario,
} from "@/lib/preview/workbench";

export default async function RunPage({
  params,
  searchParams,
}: {
  params: Promise<{ runId: string }>;
  searchParams: Promise<{ draftId?: string; courseId?: string; mode?: string; scenario?: string }>;
}) {
  const { runId } = await params;
  const resolvedSearchParams = await searchParams;
  const preview =
    resolvedSearchParams.mode === "preview"
      ? buildRunWorkbenchPreview(resolvePreviewScenario(resolvedSearchParams.scenario, "running"))
      : null;
  const shellSearchParams = new URLSearchParams();
  if (resolvedSearchParams.draftId) {
    shellSearchParams.set("draftId", resolvedSearchParams.draftId);
  }
  if (resolvedSearchParams.courseId) {
    shellSearchParams.set("courseId", resolvedSearchParams.courseId);
  }

  return (
    <AppShell
      eyebrow="Step 3"
      title="运行页"
      shellState={buildAppShellState(preview ? "/runs" : `/runs/${runId}`, shellSearchParams)}
      contextIds={
        preview
          ? {
              draftId: null,
              runId: null,
              courseId: null,
            }
          : {
              draftId: resolvedSearchParams.draftId ?? null,
              runId,
              courseId: resolvedSearchParams.courseId ?? null,
            }
      }
    >
      <RunSessionWorkbenchV2 key={preview ? `preview-${preview.scenario}` : runId} preview={preview} />
    </AppShell>
  );
}
