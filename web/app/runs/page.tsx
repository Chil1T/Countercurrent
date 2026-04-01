import { AppShell } from "@/components/app-shell";
import { RunSessionWorkbenchV2 } from "@/components/run/run-session-workbench-v2";
import { buildAppShellState } from "@/lib/app-shell-state";

export default async function RunsPage({
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
    <AppShell
      eyebrow="Step 3"
      title="运行页"
      shellState={buildAppShellState("/runs", shellSearchParams)}
      contextIds={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    >
      <RunSessionWorkbenchV2
        initialState={{
          draft_id: resolvedSearchParams.draftId ?? null,
          course_id: resolvedSearchParams.courseId ?? null,
        }}
      />
    </AppShell>
  );
}
