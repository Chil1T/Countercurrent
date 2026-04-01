"use client";

import Link from "next/link";

import { RunLogPreview, RunSession } from "@/lib/api/runs";
import { SurfaceCard } from "@/components/stitch-v2/surface-card";
import { StatusChip } from "@/components/stitch-v2/status-chip";

export function RunV2Sections({
  run,
  runHeadline,
  runSummary,
  statusTone,
  streamWarning,
  logStreamWarning,
  runLog,
  canResume,
  canClean,
  actionState,
  previewScenario,
  previewResultsHref,
  isPreview,
  onResume,
  onClean,
}: {
  run: RunSession | null;
  runHeadline: string;
  runSummary: string;
  statusTone: string;
  streamWarning: string | null;
  logStreamWarning: string | null;
  runLog: RunLogPreview | null;
  canResume: boolean;
  canClean: boolean;
  actionState: "idle" | "resuming" | "cleaning";
  previewScenario?: string;
  previewResultsHref: string;
  isPreview: boolean;
  onResume: () => void;
  onClean: () => void;
}) {
  return (
    <section className="space-y-6">
      <SurfaceCard className="overflow-hidden p-6 md:p-7 xl:p-8">
        <div className="grid gap-8 xl:grid-cols-[1.08fr_0.92fr]">
          <div>
            <p className="font-stitch-label text-[11px] uppercase tracking-[0.34em] text-[var(--stitch-shell-primary-strong)]">
              Run Mission Control
            </p>
            <h3 className="font-stitch-headline mt-4 text-4xl font-black tracking-[-0.05em] text-stone-900 md:text-5xl">
              {runHeadline}
            </h3>
            <p className="mt-5 max-w-3xl text-sm leading-8 text-stone-600 md:text-base">
              {runSummary}
            </p>
            <div className={`mt-5 inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${statusTone}`}>
              {run?.status ?? "pending"}
            </div>
          </div>

          <div className="rounded-[1.75rem] bg-[var(--stitch-shell-rail)] p-5 text-stone-100 shadow-[var(--stitch-shell-shadow-strong)]">
            <p className="font-stitch-label text-[11px] uppercase tracking-[0.3em] text-white/55">
              Run Snapshot
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <StatusChip label={run?.backend ?? "pending"} tone="accent" />
              <StatusChip label={run?.run_kind ?? "chapter"} tone="default" />
              <StatusChip label={run?.hosted ? "hosted" : "heuristic"} tone="default" />
            </div>
            {isPreview ? (
              <div className="mt-5 rounded-[1.25rem] border border-sky-200/30 bg-sky-50/10 px-4 py-3 text-sm text-sky-100">
                <span className="font-semibold uppercase tracking-[0.18em]">Preview</span>
                <span className="ml-2">当前为 {previewScenario} 示例态。</span>
              </div>
            ) : null}
          </div>
        </div>

        {run ? (
          <div className="mt-8 grid gap-3 text-sm md:grid-cols-2 2xl:grid-cols-4">
            {[
              ["Backend", run.backend],
              ["Mode", run.hosted ? "hosted" : "heuristic"],
              ["Simple Model", run.simple_model ?? "default"],
              ["Complex Model", run.complex_model ?? "default"],
              ["Base URL", run.base_url ?? "provider default"],
              ["Run Type", run.run_kind],
              ["Review Mode", run.review_enabled ? run.review_mode ?? "default" : "disabled"],
              ["Target Output", run.target_output ?? "default"],
            ].map(([label, value]) => (
              <div key={label} className="min-w-0 rounded-[1.4rem] border border-[var(--stitch-shell-border)] bg-[var(--stitch-shell-panel-soft)] px-4 py-4">
                <div className="text-[11px] uppercase tracking-[0.18em] text-stone-400">{label}</div>
                <div className="mt-2 break-all font-semibold text-stone-800">{value}</div>
              </div>
            ))}
          </div>
        ) : null}

        {streamWarning ? (
          <div className="mt-5 rounded-[1.5rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            {streamWarning}
          </div>
        ) : null}

        <div className="mt-5 flex flex-wrap items-center gap-3 text-sm">
          <button
            type="button"
            onClick={onResume}
            disabled={isPreview || !canResume || actionState !== "idle"}
            className="rounded-full bg-[var(--stitch-shell-primary)] px-4 py-2 font-semibold text-white transition hover:bg-[var(--stitch-shell-primary-strong)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {actionState === "resuming" ? "恢复中..." : "Resume"}
          </button>
          <button
            type="button"
            onClick={onClean}
            disabled={isPreview || !canClean}
            className="rounded-full border border-[var(--stitch-shell-border)] px-4 py-2 font-semibold text-stone-700 transition hover:bg-[var(--stitch-shell-panel-soft)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {actionState === "cleaning" ? "清理中..." : "Clean"}
          </button>
          {isPreview ? (
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-2 text-xs uppercase tracking-[0.14em] text-sky-700">
              Preview only
            </span>
          ) : null}
        </div>

        {run?.course_id ? (
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
            <span className="rounded-full bg-[var(--stitch-shell-panel-soft)] px-3 py-1 text-stone-700">
              课程 ID：{run.course_id}
            </span>
            {isPreview ? (
              <Link
                href={previewResultsHref}
                style={{ color: "#ffffff" }}
                className="inline-flex items-center rounded-full bg-[var(--stitch-shell-primary)] px-4 py-2 font-semibold text-white no-underline visited:text-white hover:bg-[var(--stitch-shell-primary-strong)]"
              >
                查看结果页预览
              </Link>
            ) : run.status === "completed" ? (
              <Link
                href={`/courses/${run.course_id}/results?draftId=${encodeURIComponent(run.draft_id)}&runId=${encodeURIComponent(run.id)}`}
                style={{ color: "#ffffff" }}
                className="inline-flex items-center rounded-full bg-[var(--stitch-shell-primary)] px-4 py-2 font-semibold text-white no-underline visited:text-white hover:bg-[var(--stitch-shell-primary-strong)]"
              >
                查看结果页
              </Link>
            ) : null}
          </div>
        ) : null}
      </SurfaceCard>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.9fr)]">
        <SurfaceCard className="p-6 md:p-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-[var(--stitch-shell-primary-strong)]">
                Chapter Board
              </p>
              <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-stone-900">
                章节执行
              </h4>
            </div>
            <StatusChip label={`${run?.chapter_progress?.length ?? 0} chapters`} tone="accent" />
          </div>
          <p className="mt-3 text-sm text-stone-500">并发章节进度与导出状态</p>

          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            {(run?.chapter_progress ?? []).map((chapter) => {
              const isCompleted = chapter.status === "completed";
              const isRunning = chapter.status === "running";
              const isFailed = chapter.status === "failed";
              const isExportReady = chapter.export_ready;

              let toneClass = "bg-stone-50 border-stone-200 text-stone-700";
              let badgeClass = "bg-stone-200 text-stone-600";
              let statusLabel = chapter.status;

              if (isExportReady) {
                toneClass = "bg-emerald-50 border-emerald-200 text-emerald-800";
                badgeClass = "bg-emerald-200 text-emerald-800";
                statusLabel = "export ready";
              } else if (isCompleted) {
                toneClass = "bg-stone-50 border-emerald-200 text-stone-800";
                badgeClass = "bg-emerald-100 text-emerald-700";
              } else if (isRunning) {
                toneClass = "bg-white border-amber-300 shadow-sm text-stone-800 ring-1 ring-amber-300/50";
                badgeClass = "bg-amber-100 text-amber-700 font-medium animate-pulse";
              } else if (isFailed) {
                toneClass = "bg-rose-50 border-rose-200 text-rose-800";
                badgeClass = "bg-rose-200 text-rose-800";
              }

              return (
                <div key={chapter.chapter_id} className={`rounded-[1.5rem] border p-4 transition-all duration-300 ${toneClass}`}>
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate font-semibold" title={chapter.chapter_id}>{chapter.chapter_id}</span>
                    <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] uppercase tracking-wider ${badgeClass}`}>
                      {statusLabel}
                    </span>
                  </div>
                  <div className="mt-3 flex items-end justify-between text-sm">
                    <div className="mr-3 truncate text-stone-500">
                      {chapter.current_step ? <span>当前: {chapter.current_step}</span> : <span>完成度</span>}
                    </div>
                    <div className="shrink-0 font-semibold">
                      {chapter.completed_step_count} / {chapter.total_step_count}
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-stone-400">
                    {chapter.export_ready ? "可导出最终资源" : "生成中"}
                  </div>
                </div>
              );
            })}
          </div>
        </SurfaceCard>

        <div className="flex h-full flex-col gap-6">
          <SurfaceCard tone="rail" className="p-6 md:p-7">
            <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-white/55">
              Runtime Flow
            </p>
            <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-white">
              数据通路
            </h4>
            <p className="mt-3 text-sm text-white/60">实时反映 Runtime Contract 执行流</p>
            <div className="mt-6 flex flex-col gap-0">
              {(run?.stages ?? []).map((stage, index, arr) => {
                const isCompleted = stage.status === "completed";
                const isRunning = stage.status === "running";
                const isFailed = stage.status === "failed";

                let toneClass = "bg-stone-800/30 text-stone-400 border-stone-700/50";
                let circleClass = "bg-stone-700";

                if (isCompleted) {
                  toneClass = "bg-emerald-900/20 text-emerald-300 border-emerald-800/50";
                  circleClass = "bg-emerald-500";
                } else if (isRunning) {
                  toneClass = "bg-amber-900/20 text-amber-300 border-amber-800/50";
                  circleClass = "bg-amber-400";
                } else if (isFailed) {
                  toneClass = "bg-rose-900/20 text-rose-300 border-rose-800/50";
                  circleClass = "bg-rose-500";
                }

                return (
                  <div key={stage.name} className="relative flex items-start gap-4 pb-4">
                    {index !== arr.length - 1 ? (
                      <div className={`absolute bottom-0 left-[11px] top-[24px] w-0.5 ${isCompleted ? "bg-emerald-900/50" : "bg-stone-800/50"}`} />
                    ) : null}
                    <div className="relative z-10 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--stitch-shell-rail)]">
                      <div className={`h-2.5 w-2.5 rounded-full ${circleClass}`} />
                      {isRunning ? <div className="absolute inset-0 animate-ping rounded-full border border-amber-500/30" /> : null}
                    </div>
                    <div className={`flex-1 rounded-[1.25rem] border px-4 py-3 text-sm transition-colors duration-300 ${toneClass}`}>
                      <div className="flex items-center justify-between gap-3">
                        <span className="truncate pr-2 font-medium tracking-wide">{stage.name}</span>
                        <span className="shrink-0 text-[11px] uppercase tracking-wider opacity-80">{stage.status}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </SurfaceCard>

          <SurfaceCard className="flex flex-1 flex-col p-6 md:p-7">
            <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-[var(--stitch-shell-primary-strong)]">
              Logs
            </p>
            <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-stone-900">
              错误与日志
            </h4>
            <p className="mt-3 shrink-0 text-sm leading-7 text-stone-600">
              last error：{run?.last_error ?? "none"}
            </p>
            <div className="mt-4 flex flex-1 flex-col rounded-[1.5rem] border border-[var(--stitch-shell-border)] bg-[var(--stitch-shell-panel-soft)] p-4">
              <div className="flex shrink-0 items-center justify-between gap-3 text-xs uppercase tracking-[0.16em] text-stone-500">
                <span>Run Log</span>
                <span>{runLog?.available ? "available" : "pending"}</span>
              </div>
              {logStreamWarning ? (
                <p className="mt-3 shrink-0 text-xs leading-6 text-amber-700">{logStreamWarning}</p>
              ) : null}
              <pre className="mt-3 min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words text-xs leading-6 text-stone-700">
                {runLog?.available ? runLog.content : "日志尚未生成。"}
              </pre>
              {runLog?.truncated ? (
                <p className="mt-3 shrink-0 text-xs leading-6 text-stone-500">当前只显示尾部日志预览。</p>
              ) : null}
            </div>
          </SurfaceCard>
        </div>
      </div>
    </section>
  );
}
