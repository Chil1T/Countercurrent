import { AppShell } from "@/components/app-shell";
import { ResultsWorkbenchV2 } from "@/components/results/results-workbench-v2";
import { buildAppShellState } from "@/lib/app-shell-state";

export default async function ResultsPage({
  searchParams,
}: {
  searchParams: Promise<{ draftId?: string; courseId?: string; runId?: string }>;
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
      eyebrow="Step 4"
      title="结果页"
      shellState={buildAppShellState("/courses/results", shellSearchParams)}
      contextIds={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: resolvedSearchParams.runId ?? null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    >
      <ResultsWorkbenchV2
        courseId={resolvedSearchParams.courseId ?? null}
        runId={resolvedSearchParams.runId ?? null}
      />
    </AppShell>
  );
}
