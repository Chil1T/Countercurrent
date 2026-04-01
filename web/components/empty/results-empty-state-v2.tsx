import { ReactNode } from "react";

import { EmptyStatePanel } from "@/components/stitch-v2/empty-state-panel";

export function ResultsEmptyStateV2({
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
      eyebrow="Step 4"
      title="尚无运行结果"
      description={
        contextLabel
          ? `当前上下文 ${contextLabel} 还没有可展示的文件树或导出内容。请先完成一次课程运行，结果页才会显示章节产物、review 摘要和导出入口。`
          : "当前还没有可展示的文件树或导出内容。请先完成一次课程运行，结果页才会显示章节产物、review 摘要和导出入口。"
      }
      actions={actions}
    />
  );
}
