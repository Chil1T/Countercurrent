"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StitchV4ContextRail } from "@/components/stitch-v4/context-rail";
import { StitchV4RightRail, StitchV4TopNav } from "@/components/stitch-v4/chrome";
import { StitchV4MaterialSymbol } from "@/components/stitch-v4/material-symbol";
import { useLocale } from "@/lib/locale";
import {
  cleanRun,
  getRun,
  getRunLog,
  resumeRun,
  subscribeRunEvents,
  subscribeRunLogEvents,
  type RunLogChunk,
  type RunLogPreview,
  type RunSession,
  type UnstartedRunWorkbenchState,
} from "@/lib/api/runs";
import type { ProductContext } from "@/lib/product-nav";
import type { RunWorkbenchPreview } from "@/lib/preview/workbench";

function chapterPercent(run: RunSession | null, chapterId: string): number {
  const chapter = run?.chapter_progress.find((item) => item.chapter_id === chapterId);
  if (!chapter || chapter.total_step_count === 0) {
    return 0;
  }
  return Math.round((chapter.completed_step_count / chapter.total_step_count) * 100);
}

function chapterStatusTone(status: string): string {
  if (status === "completed") {
    return "bg-[var(--stitch-primary-fixed-dim)] text-[var(--stitch-on-primary-fixed)]";
  }
  if (status === "running") {
    return "bg-[var(--stitch-primary-fixed)] text-[var(--stitch-on-primary-fixed)]";
  }
  if (status === "failed") {
    return "bg-[var(--stitch-error-container)] text-[var(--stitch-on-error-container)]";
  }
  return "bg-[var(--stitch-surface-container)] text-[var(--stitch-on-surface-variant)]";
}

export function StitchV4RunPage({
  context,
  runId = null,
  initialState = null,
  preview = null,
}: {
  context: ProductContext;
  runId?: string | null;
  initialState?: UnstartedRunWorkbenchState | null;
  preview?: RunWorkbenchPreview | null;
}) {
  const { messages, locale } = useLocale();
  const isPreview = !!preview;
  const isUnstarted = !preview && !runId;
  const [run, setRun] = useState<RunSession | null>(preview?.run ?? null);
  const [runLog, setRunLog] = useState<RunLogPreview | null>(preview?.runLog ?? null);
  const [error, setError] = useState<string | null>(null);
  const [streamWarning, setStreamWarning] = useState<string | null>(null);
  const [logStreamWarning, setLogStreamWarning] = useState<string | null>(null);
  const [actionState, setActionState] = useState<"idle" | "resuming" | "cleaning">("idle");

  useEffect(() => {
    if (preview || !runId) {
      return;
    }
    let cancelled = false;
    const activeRunId = runId;

    async function loadRun() {
      try {
        const nextRun = await getRun(activeRunId);
        if (!cancelled) {
          setRun(nextRun);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      }
    }

    void loadRun();
    const unsubscribe = subscribeRunEvents(activeRunId, {
      onUpdate: (nextRun) => {
        if (!cancelled) {
          setRun(nextRun);
          setStreamWarning(null);
          if (new Set(["completed", "failed", "cleaned"]).has(nextRun.status)) {
            setActionState("idle");
          }
        }
      },
      onError: (message) => {
        if (!cancelled) {
          setStreamWarning(message);
        }
      },
    });

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [preview, runId]);

  useEffect(() => {
    if (preview || !runId) {
      return;
    }
    let cancelled = false;
    let unsubscribe = () => {};
    const activeRunId = runId;

    async function loadLog() {
      try {
        const nextLog = await getRunLog(activeRunId);
        if (cancelled) {
          return;
        }
        setRunLog(nextLog);
        unsubscribe = subscribeRunLogEvents(activeRunId, nextLog.cursor, {
          onChunk: (chunk: RunLogChunk) => {
            if (cancelled) {
              return;
            }
            setRunLog((current) => ({
              run_id: chunk.run_id,
              available: true,
              cursor: chunk.cursor,
              content: `${current?.content ?? ""}${chunk.content}`,
              truncated: false,
            }));
            setLogStreamWarning(null);
          },
          onError: (message) => {
            if (!cancelled) {
              setLogStreamWarning(message);
            }
          },
        });
      } catch {
        if (!cancelled) {
          setRunLog(null);
        }
      }
    }

    void loadLog();
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [preview, runId, run?.status]);

  async function handleResume() {
    if (isPreview || !runId) {
      return;
    }
    setActionState("resuming");
    try {
      const nextRun = await resumeRun(runId);
      setRun(nextRun);
      setRunLog(null);
      setError(null);
    } catch (actionError) {
      setActionState("idle");
      setError(actionError instanceof Error ? actionError.message : "Unknown error");
    }
  }

  async function handleClean() {
    if (isPreview || !runId) {
      return;
    }
    setActionState("cleaning");
    try {
      const nextRun = await cleanRun(runId);
      setRun(nextRun);
      setRunLog(null);
      setActionState("idle");
      setError(null);
    } catch (actionError) {
      setActionState("idle");
      setError(actionError instanceof Error ? actionError.message : "Unknown error");
    }
  }

  const canResume = !!run && (run.status === "failed" || run.status === "completed");
  const canClean = !!run && run.status !== "running" && actionState === "idle";
  const displayRun = run;
  const nextContext = {
    draftId: context.draftId ?? initialState?.draft_id ?? displayRun?.draft_id ?? null,
    courseId: context.courseId ?? initialState?.course_id ?? displayRun?.course_id ?? null,
    runId: runId ?? context.runId,
  };
  const previewResultsHref = `/courses/preview/results?mode=preview&scenario=${preview?.scenario === "completed" ? "completed" : "running"}&runId=preview-run`;
  const runHeadline = isUnstarted
    ? messages.run.runHeadline.unstarted
    : displayRun?.status === "running"
      ? messages.run.runHeadline.running
      : displayRun?.status === "completed"
        ? messages.run.runHeadline.completed
        : displayRun?.status === "failed"
          ? messages.run.runHeadline.failed
          : displayRun?.status === "cleaned"
            ? messages.run.runHeadline.cleaned
            : messages.run.runHeadline.session;
  const chapterCards = isUnstarted
    ? ["chapter-01", "chapter-02", "chapter-03"]
    : (displayRun?.chapter_progress.map((item) => item.chapter_id) ?? []);
  const resultsHref =
    displayRun?.course_id && displayRun?.id
      ? `/courses/${displayRun.course_id}/results?draftId=${encodeURIComponent(displayRun.draft_id)}&runId=${encodeURIComponent(displayRun.id)}`
      : nextContext.courseId
        ? `/courses/${nextContext.courseId}/results`
        : "/courses/results";

  return (
    <div className="min-h-screen bg-[var(--stitch-background)] text-[var(--stitch-on-surface)]">
      <StitchV4TopNav active="run" context={nextContext} withSearch />
      <main className="flex min-h-[calc(100vh-64px)]">
        <div className="flex-1 p-8 pr-80">
          <header className="mb-10">
            <h1 className="font-stitch-headline mb-2 text-5xl font-extrabold tracking-[-0.08em]">
              {messages.run.title}
            </h1>
            <p className="max-w-2xl font-medium text-[var(--stitch-on-surface-variant)]">
              {isUnstarted
                ? messages.run.unstartedDescription
                : messages.run.runningDescription(displayRun?.course_id ?? nextContext.courseId ?? "current")}
            </p>
          </header>

          {error ? (
            <div className="mb-6 rounded-xl bg-[var(--stitch-error-container)] px-4 py-3 text-sm text-[var(--stitch-on-error-container)]">
              {error}
            </div>
          ) : null}

          <div className="mb-12 grid grid-cols-12 gap-6">
            {chapterCards.map((chapterId, index) => {
              const chapter = displayRun?.chapter_progress.find((item) => item.chapter_id === chapterId);
              const status = chapter?.status ?? "pending";
              const percent = chapterPercent(displayRun, chapterId);
              const activeRun = status === "running";
              return (
                <div
                  key={chapterId}
                  className={`col-span-12 rounded-xl p-6 shadow-sm ${
                    activeRun
                      ? "bg-[var(--stitch-surface-container-lowest)] shadow-[0_24px_40px_rgba(0,85,212,0.14)] md:col-span-8"
                      : index === 0 && status === "completed"
                        ? "bg-[var(--stitch-surface-container-lowest)] md:col-span-4"
                        : "bg-[var(--stitch-surface-container-low)] md:col-span-4"
                  }`}
                >
                  <div className="mb-6 flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-bold uppercase tracking-[0.24em] text-[var(--stitch-primary)]">
                        {chapterId}
                      </span>
                      {activeRun ? (
                        <span className="rounded-full bg-[var(--stitch-primary-fixed)] px-2 py-0.5 text-[10px] font-black text-[var(--stitch-on-primary-fixed)]">
                          {messages.run.activeRun}
                        </span>
                      ) : null}
                    </div>
                    <span className={`rounded-full px-2 py-1 text-[10px] font-bold ${chapterStatusTone(status)}`}>
                      {messages.results.statusLabel(status)}
                    </span>
                  </div>
                  <h3 className="font-stitch-headline mb-2 text-2xl font-bold">
                    {chapterId.replaceAll("-", " ").replace("chapter", locale === "zh-CN" ? "章节" : "Chapter")}
                  </h3>
                  <p className="mb-6 text-sm italic text-[var(--stitch-on-surface-variant)]">
                    {chapter?.current_step ?? (isUnstarted ? messages.run.runHeadline.unstarted : messages.run.waitingNext)}
                  </p>
                  <div className="space-y-4">
                    <div className="flex justify-between text-xs font-bold">
                      <span>{status === "pending" ? messages.run.queued : messages.results.statusLabel(status)}</span>
                      <span>{percent}%</span>
                    </div>
                    <div className="h-3 w-full overflow-hidden rounded-full bg-[var(--stitch-surface-container)]">
                      <div
                        className={`h-full rounded-full ${
                          activeRun
                            ? "bg-gradient-to-r from-[var(--stitch-primary)] to-[var(--stitch-primary-container)] shadow-[0_0_12px_rgba(29,109,255,0.4)]"
                            : status === "completed"
                              ? "bg-[var(--stitch-primary-container)]"
                              : "bg-[var(--stitch-surface-container-highest)]"
                        }`}
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}

            <div className="col-span-12 flex flex-col justify-between rounded-xl bg-[var(--stitch-primary-container)] p-6 text-white md:col-span-4">
              <div>
                <h4 className="font-stitch-headline text-lg font-bold">{messages.run.queueTitle}</h4>
                <p className="mt-1 text-xs text-white/80">
                  {isUnstarted ? messages.run.queueUnstarted : messages.run.queueRunning(chapterCards.length)}
                </p>
              </div>
              <div className="mt-6 flex flex-col gap-2">
                <button
                  type="button"
                  disabled={isPreview || !canResume || actionState !== "idle"}
                  onClick={() => void handleResume()}
                  className="w-full rounded-lg bg-white py-3 text-xs font-bold text-[var(--stitch-primary)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {actionState === "resuming" ? messages.run.resuming : messages.run.resume}
                </button>
                <button
                  type="button"
                  disabled={isPreview || !canClean}
                  onClick={() => void handleClean()}
                  className="w-full rounded-lg bg-[#1c1c16]/20 py-3 text-xs font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {actionState === "cleaning" ? messages.run.cleaning : messages.run.clean}
                </button>
                <Link
                  href={isPreview ? previewResultsHref : resultsHref}
                  className="inline-flex justify-center rounded-lg bg-[rgba(255,255,255,0.12)] py-3 text-xs font-bold"
                >
                  {messages.run.viewResults}
                </Link>
              </div>
            </div>
          </div>

          <section className="mt-8">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-stitch-headline flex items-center gap-2 text-2xl font-extrabold">
                <StitchV4MaterialSymbol name="terminal" className="text-[var(--stitch-on-surface-variant)]" />
                {messages.run.logsTitle}
              </h2>
              <div className="flex gap-4 text-[10px] font-bold">
                <span className="flex items-center gap-1 text-[var(--stitch-on-surface-variant)]">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {messages.run.systemOnline}
                </span>
                <span className="flex items-center gap-1 text-[var(--stitch-on-surface-variant)]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[var(--stitch-primary)]" />
                  {isUnstarted ? messages.run.idle : messages.run.streaming}
                </span>
              </div>
            </div>
            <div className="overflow-hidden rounded-xl bg-[var(--stitch-inverse-surface)] shadow-2xl">
              <div className="flex items-center gap-2 bg-[#474746] px-4 py-2">
                <div className="h-2.5 w-2.5 rounded-full bg-red-500/30" />
                <div className="h-2.5 w-2.5 rounded-full bg-yellow-500/30" />
                <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/30" />
                <span className="ml-4 text-[10px] uppercase tracking-widest text-white/40">
                  course_production_v4.log
                </span>
              </div>
              <div className="h-64 overflow-y-auto p-6 font-mono text-xs leading-relaxed text-white/90">
                {isUnstarted ? (
                  <div>{messages.run.noLog}</div>
                ) : (
                  <pre className="whitespace-pre-wrap">{runLog?.content || messages.run.waitingLog}</pre>
                )}
              </div>
            </div>
            {streamWarning || logStreamWarning ? (
              <div className="mt-4 rounded-xl bg-[var(--stitch-surface-container-low)] px-4 py-3 text-sm text-[var(--stitch-on-surface-variant)]">
                {[streamWarning, logStreamWarning].filter(Boolean).join(" / ")}
              </div>
            ) : null}
          </section>
        </div>

        <StitchV4RightRail title={messages.common.context} subtitle={messages.common.activeSession}>
          <StitchV4ContextRail
            draftId={nextContext.draftId}
            courseId={nextContext.courseId}
            runId={nextContext.runId}
            prefix={
              <section className="rounded-xl bg-[#474746] p-5">
                <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-[#dddad0]/70">
                  {messages.run.snapshotTitle}
                </h3>
                <div className="space-y-3 text-sm text-[#f4f1e7]">
                  <div>{messages.run.statusLabel} · {runHeadline}</div>
                  <div>{messages.run.backendLabel} · {displayRun?.backend ?? messages.common.pending}</div>
                  <div>{messages.run.targetLabel} · {displayRun?.target_output ?? messages.common.notConfigured}</div>
                  <div>{messages.run.snapshotLabel} · {displayRun?.snapshot_complete ? messages.run.snapshotComplete : messages.run.snapshotPending}</div>
                  <div>{messages.run.reviewLabel} · {displayRun?.review_enabled ? displayRun.review_mode ?? messages.common.yes : messages.config.disabled}</div>
                </div>
              </section>
            }
            suffix={
              <section className="rounded-xl bg-[#474746] p-5">
                <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-[#dddad0]/70">
                  {messages.run.stageRailTitle}
                </h3>
                <ul className="space-y-2 text-sm text-[#f4f1e7]">
                  {(displayRun?.stages ?? []).map((stage) => (
                    <li key={stage.name}>
                      {stage.name} · {messages.results.statusLabel(stage.status)}
                    </li>
                  ))}
                  {isUnstarted ? <li>{messages.run.runHeadline.unstarted}</li> : null}
                </ul>
              </section>
            }
          />
        </StitchV4RightRail>
      </main>
    </div>
  );
}
