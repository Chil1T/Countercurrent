import { AppShell } from "@/components/app-shell";
import { CourseDraftWorkbenchV2 } from "@/components/input/course-draft-workbench-v2";
import { buildAppShellState } from "@/lib/app-shell-state";

export default async function InputPage({
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
      eyebrow="Step 1"
      title="输入页"
      shellState={buildAppShellState("/courses/new/input", shellSearchParams)}
      contextIds={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: resolvedSearchParams.runId ?? null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    >
      <CourseDraftWorkbenchV2 initialDraftId={resolvedSearchParams.draftId ?? null} />
    </AppShell>
  );
}
