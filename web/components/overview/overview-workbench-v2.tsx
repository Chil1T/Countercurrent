import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { StatusChip } from "@/components/stitch-v2/status-chip";
import { SurfaceCard } from "@/components/stitch-v2/surface-card";
import { AppShellState, buildAppShellState } from "@/lib/app-shell-state";

export function OverviewWorkbenchV2({
  shellState = buildAppShellState("/", new URLSearchParams()),
}: {
  shellState?: AppShellState;
}) {
  return (
    <AppShell eyebrow="Overview" title="Course Production Workbench" shellState={shellState}>
      <section className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
        <SurfaceCard className="overflow-hidden p-6 md:p-7 xl:p-8">
          <div className="flex flex-wrap items-center gap-3">
            <StatusChip label="Workspace Overview" tone="accent" />
            <StatusChip label="Stitch V2 Foundation" />
          </div>

          <h2 className="font-stitch-headline mt-5 max-w-3xl text-4xl font-black tracking-[-0.05em] text-stone-900 md:text-5xl">
            把 blueprint-first CLI 组织成一个面向课程生产者的成体系工作台。
          </h2>
          <p className="mt-5 max-w-3xl text-sm leading-8 text-stone-600 md:text-base">
            当前工作流围绕四步展开：组织输入、配置模板、监控运行、审阅结果。V2
            壳层负责把这四个动作放到更清晰的产品叙事里，而不是增加新的假入口。
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {[
              ["输入", "以本地字幕和手工章节资产为主入口，继续保持无课程链接的产品决策。"],
              ["配置", "模板与 AI 服务配置仍然是真实主路径，高级隐藏控制不会借 V2 回流。"],
              ["运行", "继续展示实时章节进度、数据通路摘要、日志和可恢复动作。"],
              ["结果", "保持课程级状态来源、稳定树刷新与过滤导出语义不变。"],
            ].map(([label, copy]) => (
              <SurfaceCard key={label} className="p-5" tone="muted">
                <div className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-[var(--stitch-shell-primary-strong)]">
                  {label}
                </div>
                <p className="mt-3 text-sm leading-7 text-stone-700">{copy}</p>
              </SurfaceCard>
            ))}
          </div>
        </SurfaceCard>

        <SurfaceCard className="p-6 md:p-7 xl:p-8" tone="rail">
          <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-stone-400">
            Guided Entry
          </p>
          <h3 className="font-stitch-headline mt-4 text-3xl font-black tracking-[-0.05em] text-white">
            从当前产品步骤进入，不需要 preview-only 语义。
          </h3>
          <div className="mt-6 space-y-3">
            {shellState.navItems.map((item) =>
              item.enabled && item.href ? (
                <Link
                  key={item.label}
                  href={item.href}
                  className="block rounded-[22px] border border-white/10 bg-white/6 px-5 py-4 transition hover:bg-white/10"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-stitch-label text-[11px] uppercase tracking-[0.24em] text-stone-400">
                        Step {item.step}
                      </div>
                      <div className="mt-2 text-lg font-semibold text-white">{item.label}</div>
                    </div>
                    <StatusChip label={item.hint} tone="muted" />
                  </div>
                </Link>
              ) : (
                <div
                  key={item.label}
                  className="rounded-[22px] border border-dashed border-white/10 bg-white/5 px-5 py-4 text-stone-400"
                >
                  <div className="font-stitch-label text-[11px] uppercase tracking-[0.24em]">
                    Step {item.step}
                  </div>
                  <div className="mt-2 text-lg font-semibold">{item.label}</div>
                  <div className="mt-1 text-sm">需要先创建真实草稿或运行会话</div>
                </div>
              ),
            )}
          </div>
        </SurfaceCard>
      </section>
    </AppShell>
  );
}
