import { ResultsWorkbench } from "@/components/results/results-workbench";
import { AppShell } from "@/components/app-shell";
import { buildAppShellState } from "@/lib/app-shell-state";

export default async function ResultsPage({
  params,
  searchParams,
}: {
  params: Promise<{ courseId: string }>;
  searchParams: Promise<{ draftId?: string; runId?: string }>;
}) {
  const { courseId } = await params;
  const resolvedSearchParams = await searchParams;
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
      shellState={buildAppShellState(`/courses/${courseId}/results`, shellSearchParams)}
      contextIds={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: resolvedSearchParams.runId ?? null,
        courseId,
      }}
      >
      <ResultsWorkbench courseId={courseId} runId={resolvedSearchParams.runId ?? null} />
    </AppShell>
  );
}
