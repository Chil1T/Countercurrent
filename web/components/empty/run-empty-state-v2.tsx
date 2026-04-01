import { ReactNode } from "react";

import { EmptyStatePanel } from "@/components/stitch-v2/empty-state-panel";

export function RunEmptyStateV2({
  draftId,
  courseId,
  actions,
}: {
  draftId?: string | null;
  courseId?: string | null;
  actions?: ReactNode;
}) {
  const contextLabel = [draftId ? `draft ${draftId}` : null, courseId ? `course ${courseId}` : null]
    .filter(Boolean)
    .join(" / ");

  return (
    <EmptyStatePanel
      eyebrow="Step 3"
      title="尚未创建运行"
      description={
        contextLabel
          ? `当前上下文 ${contextLabel} 还没有可展示的运行内容。请先在配置页保存模板配置并启动运行，随后这里会显示章节进度、数据通路和日志。`
          : "当前还没有可展示的运行内容。请先在配置页保存模板配置并启动运行，随后这里会显示章节进度、数据通路和日志。"
      }
      actions={actions}
    />
  );
}
