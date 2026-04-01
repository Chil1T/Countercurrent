import { RunEmptyStateV2 } from "@/components/empty/run-empty-state-v2";
import { buildAppShellState } from "@/lib/app-shell-state";

export default async function RunsEmptyPage({
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
    <RunEmptyStateV2
      shellState={buildAppShellState("/runs", shellSearchParams)}
      contextIds={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    />
  );
}
