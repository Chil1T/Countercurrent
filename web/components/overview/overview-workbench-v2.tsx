import Link from "next/link";

import { AppShellState } from "@/lib/app-shell-state";
import { SurfaceCard } from "@/components/stitch-v2/surface-card";

export function OverviewWorkbenchV2({ shellState }: { shellState: AppShellState }) {
  return (
    <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <SurfaceCard className="overflow-hidden bg-[linear-gradient(135deg,rgba(255,255,255,0.96),rgba(244,239,229,0.9))] p-6 md:p-7 xl:p-8">
        <div className="grid gap-8 xl:grid-cols-[1.05fr_0.95fr]">
          <div>
            <p className="font-stitch-label text-[11px] uppercase tracking-[0.34em] text-[var(--stitch-shell-primary-strong)]">
              Workspace Overview
            </p>
            <h3 className="font-stitch-headline mt-4 max-w-2xl text-4xl font-black tracking-[-0.05em] text-stone-900 md:text-5xl">
              Course Production Workbench
            </h3>
            <p className="mt-5 max-w-2xl text-sm leading-8 text-stone-600 md:text-base">
              用 Stitch V2 的叙事骨架承接现有四步产品流，让课程素材输入、模板配置、运行监控与结果复核保持一条连续工作台。
            </p>

            <div className="mt-8 grid gap-3 md:grid-cols-2">
              {[
                "本地字幕与多章节素材输入",
                "模板与 AI 服务配置",
                "运行状态、日志与恢复控制",
                "结果树、预览与过滤导出",
              ].map((item) => (
                <div
                  key={item}
                  className="rounded-[1.5rem] border border-[var(--stitch-shell-border)] bg-white/84 px-4 py-4 text-sm font-medium text-stone-700 shadow-[var(--stitch-shell-shadow-soft)]"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[1.75rem] bg-[var(--stitch-shell-rail)] p-5 text-stone-100 shadow-[var(--stitch-shell-shadow-strong)]">
            <p className="font-stitch-label text-[11px] uppercase tracking-[0.3em] text-white/55">
              Next Actions
            </p>
            <div className="mt-5 space-y-3">
              {shellState.navItems.map((item) =>
                item.enabled && item.href ? (
                  <Link
                    key={item.label}
                    href={item.href}
                    className="block rounded-[1.5rem] border border-white/10 bg-white/8 px-4 py-4 transition hover:bg-white/12"
                  >
                    <div className="font-stitch-label text-[11px] uppercase tracking-[0.26em] text-white/45">
                      {item.step}
                    </div>
                    <div className="mt-2 text-base font-semibold text-white">
                      {item.label}
                    </div>
                    <div className="mt-2 text-sm leading-7 text-white/68">{item.hint}</div>
                  </Link>
                ) : (
                  <div
                    key={item.label}
                    className="rounded-[1.5rem] border border-dashed border-white/14 bg-white/5 px-4 py-4 text-white/48"
                  >
                    <div className="font-stitch-label text-[11px] uppercase tracking-[0.26em]">
                      {item.step}
                    </div>
                    <div className="mt-2 text-base font-semibold">{item.label}</div>
                    <div className="mt-2 text-sm leading-7">
                      需要先创建真实草稿或运行上下文。
                    </div>
                  </div>
                ),
              )}
            </div>
          </div>
        </div>
      </SurfaceCard>
    </section>
  );
}
