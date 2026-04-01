import Link from "next/link";

import { ShellAction } from "@/components/stitch-v2/shell-action";
import { StatusChip } from "@/components/stitch-v2/status-chip";
import { SurfaceCard } from "@/components/stitch-v2/surface-card";
import type { AppShellState } from "@/lib/app-shell-state";

const workflowCards = [
  {
    step: "01",
    title: "Source Input",
    copy: "本地字幕与手工章节资产继续作为当前课程生产链路的真实入口。",
    accent: "upload_file",
  },
  {
    step: "02",
    title: "Template Configuration",
    copy: "AI 服务配置与模板参数仍然控制真实产物结构，不回流隐藏覆盖入口。",
    accent: "tune",
  },
  {
    step: "03",
    title: "Runtime Monitoring",
    copy: "运行页继续承接章节并发、数据通路、日志与可恢复动作。",
    accent: "monitoring",
  },
  {
    step: "04",
    title: "Results Review",
    copy: "结果页继续保留课程级状态、文件树稳定刷新与过滤导出语义。",
    accent: "inventory_2",
  },
] as const;

export function OverviewV2Sections({
  shellState,
}: {
  shellState: AppShellState;
}) {
  return (
    <section className="grid gap-8 xl:grid-cols-[1.08fr_0.92fr]">
      <SurfaceCard className="overflow-hidden p-8 md:p-10" tone="muted">
        <div className="mb-10 flex items-end justify-between gap-6">
          <div className="max-w-3xl">
            <span className="font-stitch-label mb-4 block text-xs font-bold uppercase tracking-[0.2em] text-[var(--stitch-shell-primary)]">
              Workspace Overview
            </span>
            <h2 className="font-stitch-headline max-w-3xl text-5xl font-extrabold leading-[0.95] tracking-[-0.06em] text-[var(--stitch-on-surface)] md:text-6xl">
              Course Production
              <br />
              Workbench
            </h2>
          </div>
          <div className="hidden items-center gap-4 xl:flex">
            <div className="text-right">
              <p className="font-stitch-label text-xs font-bold uppercase tracking-[0.2em] text-[var(--stitch-on-secondary-container)]">
                Live Status
              </p>
              <p className="mt-1 text-sm font-medium text-[var(--stitch-on-surface)]">
                Shell Alignment Active
              </p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-[var(--stitch-primary-container)]">
              <div className="h-2.5 w-2.5 rounded-full bg-[var(--stitch-shell-primary)]" />
            </div>
          </div>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          {workflowCards.map((card) => (
            <SurfaceCard
              key={card.step}
              className="flex h-full flex-col justify-between rounded-[2rem] p-6"
              tone={card.step === "02" ? "rail" : "default"}
            >
              <div>
                <div className="mb-8 flex items-start justify-between gap-6">
                  <span
                    className={`font-stitch-headline text-5xl font-black tracking-[-0.08em] ${
                      card.step === "02" ? "text-white/15" : "text-[var(--stitch-outline-variant)]"
                    }`}
                  >
                    {card.step}
                  </span>
                  <StatusChip
                    label={card.accent}
                    tone={card.step === "02" ? "muted" : "accent"}
                  />
                </div>
                <h3
                  className={`font-stitch-headline text-2xl font-bold tracking-[-0.04em] ${
                    card.step === "02" ? "text-white" : "text-[var(--stitch-on-surface)]"
                  }`}
                >
                  {card.title}
                </h3>
                <p
                  className={`mt-4 text-sm leading-7 ${
                    card.step === "02" ? "text-white/75" : "text-[var(--stitch-on-secondary-container)]"
                  }`}
                >
                  {card.copy}
                </p>
              </div>
              <div className="mt-8">
                <div
                  className={`rounded-xl px-4 py-3 text-xs font-bold uppercase tracking-[0.18em] ${
                    card.step === "02"
                      ? "bg-white/8 text-white/80"
                      : "bg-[var(--stitch-surface-container-lowest)] text-[var(--stitch-on-surface)]"
                  }`}
                >
                  {card.step === "01"
                    ? "本地字幕 / 手工章节资产"
                    : card.step === "02"
                      ? "AI 服务配置 / 模板"
                      : card.step === "03"
                        ? "章节并发 / 日志"
                        : "文件树 / 导出"}
                </div>
              </div>
            </SurfaceCard>
          ))}
        </div>
      </SurfaceCard>

      <SurfaceCard className="p-8 md:p-10" tone="rail">
        <p className="font-stitch-label text-xs font-bold uppercase tracking-[0.2em] text-[var(--stitch-primary-fixed-dim)]">
          Guided Entry
        </p>
        <h3 className="font-stitch-headline mt-5 text-4xl font-extrabold leading-tight tracking-[-0.05em] text-white">
          从当前产品步骤进入，
          <br />
          不用借 preview 语义。
        </h3>

        <div className="mt-8 space-y-3">
          {shellState.navItems.map((item) =>
            item.enabled && item.href ? (
              <Link
                key={item.label}
                href={item.href}
                className="block rounded-[1.5rem] border border-white/10 bg-white/6 px-5 py-5 transition hover:bg-white/10"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="font-stitch-label text-[11px] uppercase tracking-[0.24em] text-white/55">
                      Step {item.step}
                    </div>
                    <div className="mt-2 text-lg font-semibold text-white">{item.label}</div>
                    <div className="mt-1 text-sm text-white/65">{item.hint}</div>
                  </div>
                  <StatusChip label="Open" tone="muted" />
                </div>
              </Link>
            ) : (
              <div
                key={item.label}
                className="rounded-[1.5rem] border border-dashed border-white/10 bg-white/5 px-5 py-5 text-white/55"
              >
                <div className="font-stitch-label text-[11px] uppercase tracking-[0.24em]">
                  Step {item.step}
                </div>
                <div className="mt-2 text-lg font-semibold text-white">{item.label}</div>
                <div className="mt-1 text-sm">需要先创建真实草稿或运行会话</div>
              </div>
            ),
          )}
        </div>

        <div className="mt-8 space-y-3 border-t border-white/10 pt-6">
          <div className="flex flex-wrap items-center gap-3">
            <ShellAction tone="primary" href={shellState.navItems[0]?.href}>
              从输入开始
            </ShellAction>
            <ShellAction tone="ghost" href={shellState.navItems[3]?.href}>
              查看结果空态
            </ShellAction>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/6 px-4 py-4">
              <div className="font-stitch-label text-[11px] uppercase tracking-[0.24em] text-white/45">
                即将到来
              </div>
              <div className="mt-2 text-sm font-semibold text-white">Workspace Publishing</div>
              <p className="mt-2 text-sm leading-6 text-white/65">
                发布与归档会在后续真正接入结果发布链路前保持占位提示，不伪装成已可用主功能。
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/6 px-4 py-4">
              <div className="font-stitch-label text-[11px] uppercase tracking-[0.24em] text-white/45">
                Current Scope
              </div>
              <div className="mt-2 text-sm font-semibold text-white">本地素材优先</div>
              <p className="mt-2 text-sm leading-6 text-white/65">
                输入、配置、运行、结果都继续服务当前已接好的 GUI 真正主路径，不引入新的假入口。
              </p>
            </div>
          </div>
        </div>
      </SurfaceCard>
    </section>
  );
}
