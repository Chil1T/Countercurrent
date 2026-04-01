import { ResultsEmptyStateV2 } from "@/components/empty/results-empty-state-v2";
import { buildAppShellState } from "@/lib/app-shell-state";

export default async function ResultsEmptyPage({
  searchParams,
}: {
  searchParams: Promise<{ draftId?: string; courseId?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  const shellSearchParams = new URLSearchParams();
  if (resolvedSearchParams.draftId) {
    shellSearchParams.set("draftId", resolvedSearchParams.draftId);
  }
  if (resolvedSearchParams.courseId) {
    shellSearchParams.set("courseId", resolvedSearchParams.courseId);
  }

  return (
    <ResultsEmptyStateV2
      shellState={buildAppShellState("/courses/results", shellSearchParams)}
      contextIds={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    />
  );
}
