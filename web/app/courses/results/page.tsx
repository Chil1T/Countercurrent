import { AppShell } from "@/components/app-shell";
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
    <AppShell
      eyebrow="Step 4"
      title="结果页"
      shellState={buildAppShellState("/courses/results", shellSearchParams)}
      contextIds={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    >
      <section className="rounded-[28px] border border-stone-200 bg-white p-6 xl:p-7">
        <h3 className="text-xl font-semibold">尚无运行结果</h3>
        <p className="mt-3 text-sm leading-7 text-stone-600">
          当前还没有可展示的文件树或导出内容。请先完成一次课程运行，结果页才会显示章节产物、review 摘要和导出入口。
        </p>
        <div className="mt-6 rounded-[24px] border border-dashed border-stone-300 bg-stone-50 px-5 py-5 text-sm leading-7 text-stone-500">
          结果页空态只用于产品流程导航；内部 UI 调试请显式使用 `mode=preview` 的调试路由。
        </div>
      </section>
    </AppShell>
  );
}
