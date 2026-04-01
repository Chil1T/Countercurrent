import { AppShell } from "@/components/app-shell";
import { EmptyStatePanel } from "@/components/stitch-v2/empty-state-panel";
import { AppShellState } from "@/lib/app-shell-state";

export function RunEmptyStateV2({
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
    <AppShell eyebrow="Step 3" title="运行页" shellState={shellState} contextIds={contextIds}>
      <EmptyStatePanel
        eyebrow="Product Empty State"
        title="尚未创建运行"
        description="当前还没有可展示的运行内容。请先在配置页保存模板配置并启动运行，完成后这里会显示章节进度、数据通路和日志。运行页空态只用于产品流程导航；内部 UI 调试请显式使用 mode=preview 的调试路由。"
      />
    </AppShell>
  );
}
