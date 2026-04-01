import { AppShell } from "@/components/app-shell";
import { EmptyStatePanel } from "@/components/stitch-v2/empty-state-panel";
import { AppShellState } from "@/lib/app-shell-state";

export function ResultsEmptyStateV2({
  shellState,
  contextIds,
}: {
  shellState: AppShellState;
  contextIds?: {
    draftId?: string | null;
    runId?: string | null;
    courseId?: string | null;
  };
}) {
  return (
    <AppShell eyebrow="Step 4" title="结果页" shellState={shellState} contextIds={contextIds}>
      <EmptyStatePanel
        eyebrow="Product Empty State"
        title="尚无运行结果"
        description="当前还没有可展示的文件树或导出内容。请先完成一次课程运行，结果页才会显示章节产物、review 摘要和导出入口。结果页空态只用于产品流程导航；内部 UI 调试请显式使用 mode=preview 的调试路由。"
      />
    </AppShell>
  );
}
