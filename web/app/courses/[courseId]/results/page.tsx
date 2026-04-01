import { ResultsWorkbench } from "@/components/results/results-workbench";
import { AppShell } from "@/components/app-shell";
import { buildAppShellState } from "@/lib/app-shell-state";
import {
  buildResultsWorkbenchPreview,
  resolvePreviewScenario,
} from "@/lib/preview/workbench";

export default async function ResultsPage({
  params,
  searchParams,
}: {
  params: Promise<{ courseId: string }>;
  searchParams: Promise<{ draftId?: string; runId?: string; mode?: string; scenario?: string }>;
}) {
  const { courseId } = await params;
  const resolvedSearchParams = await searchParams;
  const preview =
    resolvedSearchParams.mode === "preview"
      ? buildResultsWorkbenchPreview(resolvePreviewScenario(resolvedSearchParams.scenario, "completed"))
      : null;
  const shellSearchParams = new URLSearchParams();
  if (resolvedSearchParams.draftId) {
    shellSearchParams.set("draftId", resolvedSearchParams.draftId);
  }
  if (resolvedSearchParams.runId) {
    shellSearchParams.set("runId", resolvedSearchParams.runId);
  }

  return (
    <AppShell
      eyebrow="Step 4"
      title="结果页"
      shellState={buildAppShellState(preview ? "/courses/results" : `/courses/${courseId}/results`, shellSearchParams)}
      contextIds={{
        draftId: preview ? null : (resolvedSearchParams.draftId ?? null),
        runId: preview ? null : (resolvedSearchParams.runId ?? null),
        courseId: preview ? null : courseId,
      }}
      >
      <ResultsWorkbench
        key={preview ? `preview-${preview.scenario}` : `${courseId}:${resolvedSearchParams.runId ?? "course"}`}
        courseId={courseId}
        runId={resolvedSearchParams.runId ?? null}
        preview={preview}
      />
    </AppShell>
  );
}
