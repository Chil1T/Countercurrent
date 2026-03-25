import { AppShell } from "@/components/app-shell";
import { RunSessionWorkbench } from "@/components/run/run-session-workbench";
import { buildAppShellState } from "@/lib/app-shell-state";

export default async function RunPage({
  params,
  searchParams,
}: {
  params: Promise<{ runId: string }>;
  searchParams: Promise<{ draftId?: string; courseId?: string }>;
}) {
  const { runId } = await params;
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
      shellState={buildAppShellState(`/runs/${runId}`, shellSearchParams)}
      contextIds={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    >
      <RunSessionWorkbench />
    </AppShell>
  );
}
