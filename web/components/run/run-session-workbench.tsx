"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import {
  cleanRun,
  getRunLog,
  getRun,
  RunLogChunk,
  RunLogPreview,
  resumeRun,
  RunSession,
  subscribeRunLogEvents,
  subscribeRunEvents,
} from "@/lib/api/runs";

export function RunSessionWorkbench() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;

  const [run, setRun] = useState<RunSession | null>(null);
  const [runLog, setRunLog] = useState<RunLogPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamWarning, setStreamWarning] = useState<string | null>(null);
  const [logStreamWarning, setLogStreamWarning] = useState<string | null>(null);
  const [actionState, setActionState] = useState<"idle" | "resuming" | "cleaning">("idle");

  useEffect(() => {
    let cancelled = false;

    async function loadRun() {
      try {
        const nextRun = await getRun(runId);
        if (!cancelled) {
          setRun(nextRun);
          setError(null);
          setStreamWarning(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      }
    }

    void loadRun();
    const unsubscribe = subscribeRunEvents(runId, {
      onUpdate: (nextRun) => {
        if (!cancelled) {
          setRun(nextRun);
          setError(null);
          setStreamWarning(null);
          if (nextRun.status === "completed" || nextRun.status === "failed" || nextRun.status === "cleaned") {
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
  }, [runId]);

  useEffect(() => {
    let cancelled = false;
    let unsubscribe = () => {};

    async function loadRunLog() {
      try {
        const nextLog = await getRunLog(runId);
        if (!cancelled) {
          setRunLog(nextLog);
          setLogStreamWarning(null);
          unsubscribe = subscribeRunLogEvents(runId, nextLog.cursor, {
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
        }
      } catch {
        if (!cancelled) {
          setRunLog(null);
        }
      }
    }

    void loadRunLog();

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [runId, run?.status]);

  async function handleResume() {
    setActionState("resuming");
    setError(null);
    setStreamWarning(null);
    setLogStreamWarning(null);
    try {
      const nextRun = await resumeRun(runId);
      setRun(nextRun);
      setRunLog(null);
    } catch (actionError) {
      setActionState("idle");
      setError(actionError instanceof Error ? actionError.message : "Unknown error");
    }
  }

  async function handleClean() {
    setActionState("cleaning");
    setError(null);
    setStreamWarning(null);
    setLogStreamWarning(null);
    try {
      const nextRun = await cleanRun(runId);
      setRun(nextRun);
      setRunLog(null);
      setActionState("idle");
    } catch (actionError) {
      setActionState("idle");
      setError(actionError instanceof Error ? actionError.message : "Unknown error");
    }
  }

  const canResume = run?.status === "failed" || run?.status === "completed";
  const canClean = !!run && run.status !== "running" && actionState === "idle";
  const isGlobalRun = run?.run_kind === "global";
  const runHeadline =
    run?.status === "running"
      ? "正在执行"
      : run?.status === "completed"
        ? "运行已完成"
        : run?.status === "failed"
          ? "运行失败"
          : run?.status === "cleaned"
            ? "运行已清理"
            : "等待运行";
  const backendSummary = run?.hosted
    ? `当前运行使用 hosted backend：${run.backend}`
    : "当前运行使用 heuristic backend，本次不会调用远程模型 API。";
  const runSummary =
    run?.status === "running"
      ? `${backendSummary} ${isGlobalRun ? "当前正在重建全局汇总。" : "当前正在生成章节产物。若输入样本很短，完成时间可能只有几秒。"}`
      : run?.status === "completed"
        ? `${backendSummary} ${isGlobalRun ? "全局汇总已完成更新。" : "当前运行已经完成。若阶段全部为 completed，表示本次执行已成功落盘到结果目录。"}`
        : run?.status === "failed"
          ? "运行在中途失败。请先查看 last error 和日志，再决定是否 resume。"
          : run?.status === "cleaned"
            ? "运行产物已被清理，阶段轨道已重置。当前不会继续执行，需回到配置页重新启动 / 继续运行。"
            : "运行尚未开始。";
  const statusTone =
    run?.status === "completed"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : run?.status === "failed"
        ? "bg-rose-50 text-rose-700 border-rose-200"
        : run?.status === "running"
          ? "bg-amber-50 text-amber-700 border-amber-200"
          : "bg-stone-100 text-stone-700 border-stone-200";

  if (error) {
    return (
      <div className="rounded-[28px] border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
        {error}
      </div>
    );
  }

  return (
    <section className="space-y-5">
      <div className="rounded-[28px] border border-stone-200 bg-stone-50 p-5 xl:p-6">
        <h3 className="text-xl font-semibold">运行总状态</h3>
        <div className={`mt-4 inline-flex rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] ${statusTone}`}>
          {runHeadline}
        </div>
        <p className="mt-3 text-sm leading-7 text-stone-600">
          当前运行：{run?.id ?? "加载中..."} / 状态：{run?.status ?? "pending"}
        </p>
        <p className="mt-2 text-sm leading-7 text-stone-500">
          {runSummary}
        </p>
        {run ? (
          <div className="mt-4 grid gap-3 text-sm md:grid-cols-2 2xl:grid-cols-3">
            <div className="min-w-0 rounded-2xl border border-stone-200 bg-white px-4 py-3">
              <div className="text-xs uppercase tracking-[0.16em] text-stone-400">Backend</div>
              <div className="mt-1 font-medium text-stone-800">{run.backend}</div>
            </div>
            <div className="min-w-0 rounded-2xl border border-stone-200 bg-white px-4 py-3">
              <div className="text-xs uppercase tracking-[0.16em] text-stone-400">Mode</div>
              <div className="mt-1 font-medium text-stone-800">{run.hosted ? "hosted" : "heuristic"}</div>
            </div>
            <div className="min-w-0 rounded-2xl border border-stone-200 bg-white px-4 py-3">
              <div className="text-xs uppercase tracking-[0.16em] text-stone-400">Simple Model</div>
              <div className="mt-1 font-medium text-stone-800">{run.simple_model ?? "default"}</div>
            </div>
            <div className="min-w-0 rounded-2xl border border-stone-200 bg-white px-4 py-3">
              <div className="text-xs uppercase tracking-[0.16em] text-stone-400">Complex Model</div>
              <div className="mt-1 font-medium text-stone-800">{run.complex_model ?? "default"}</div>
            </div>
            <div className="min-w-0 rounded-2xl border border-stone-200 bg-white px-4 py-3">
              <div className="text-xs uppercase tracking-[0.16em] text-stone-400">Base URL</div>
              <div className="mt-1 break-all font-medium text-stone-800">{run.base_url ?? "provider default"}</div>
            </div>
            <div className="min-w-0 rounded-2xl border border-stone-200 bg-white px-4 py-3">
              <div className="text-xs uppercase tracking-[0.16em] text-stone-400">Run Type</div>
              <div className="mt-1 font-medium text-stone-800">{run.run_kind}</div>
            </div>
            <div className="min-w-0 rounded-2xl border border-stone-200 bg-white px-4 py-3">
              <div className="text-xs uppercase tracking-[0.16em] text-stone-400">Review Mode</div>
              <div className="mt-1 font-medium text-stone-800">
                {run.review_enabled ? run.review_mode ?? "default" : "disabled"}
              </div>
            </div>
            <div className="min-w-0 rounded-2xl border border-stone-200 bg-white px-4 py-3">
              <div className="text-xs uppercase tracking-[0.16em] text-stone-400">Target Output</div>
              <div className="mt-1 font-medium text-stone-800">{run.target_output ?? "default"}</div>
            </div>
          </div>
        ) : null}
        {streamWarning ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            {streamWarning}
          </div>
        ) : null}
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
          <button
            type="button"
            onClick={() => void handleResume()}
            disabled={!canResume || actionState !== "idle"}
            className="rounded-full bg-stone-900 px-4 py-2 font-medium text-white transition hover:bg-stone-700 disabled:cursor-not-allowed disabled:bg-stone-400"
          >
            {actionState === "resuming" ? "恢复中..." : "Resume"}
          </button>
          <button
            type="button"
            onClick={() => void handleClean()}
            disabled={!canClean}
            className="rounded-full border border-stone-300 px-4 py-2 font-medium text-stone-700 transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
          >
            {actionState === "cleaning" ? "清理中..." : "Clean"}
          </button>
        </div>
        {run?.course_id ? (
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
            <span className="rounded-full bg-stone-200 px-3 py-1 text-stone-700">
              课程 ID：{run.course_id}
            </span>
            {run.status === "completed" ? (
              <Link
                href={`/courses/${run.course_id}/results?draftId=${encodeURIComponent(run.draft_id)}&runId=${encodeURIComponent(run.id)}`}
                style={{ color: "#ffffff" }}
                className="inline-flex items-center rounded-full bg-stone-900 px-4 py-2 font-medium text-white no-underline visited:text-white hover:bg-stone-700"
              >
                查看结果页
              </Link>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.9fr)]">
        <div className="min-w-0 rounded-[28px] border border-stone-200 bg-[#15120f] p-5 xl:p-6 text-stone-100">
            <h3 className="text-lg font-semibold">数据通路</h3>
            <p className="mt-2 mb-6 text-sm text-stone-400">
              实时反映 Runtime Contract 执行流
            </p>
            <div className="flex flex-col gap-0">
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
                    {index !== arr.length - 1 && (
                      <div className={`absolute left-[11px] top-[24px] bottom-0 w-0.5 ${isCompleted ? "bg-emerald-900/50" : "bg-stone-800/50"}`} />
                    )}
                    <div className="relative z-10 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#15120f]">
                      <div className={`h-2.5 w-2.5 rounded-full ${circleClass}`} />
                      {isRunning && (
                        <div className="absolute inset-0 rounded-full border border-amber-500/30 animate-ping" />
                      )}
                    </div>
                    <div className={`flex-1 rounded-2xl border px-4 py-3 text-sm transition-colors duration-300 ${toneClass}`}>
                      <div className="flex items-center justify-between">
                        <span className="font-medium tracking-wide">{stage.name}</span>
                        <span className="text-[11px] uppercase tracking-wider opacity-80">{stage.status}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
              {(!run?.stages || run.stages.length === 0) && (
                <div className="text-sm text-stone-500">尚无运行流数据</div>
              )}
            </div>
        </div>
        <div className="min-w-0 rounded-[28px] border border-stone-200 bg-white p-5">
          <h3 className="text-lg font-semibold">错误与日志</h3>
          <p className="mt-3 text-sm leading-7 text-stone-600">
            last error：{run?.last_error ?? "none"}
          </p>
          <div className="mt-4 rounded-2xl border border-stone-200 bg-stone-50 p-4">
            <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.16em] text-stone-500">
              <span>Run Log</span>
              <span>{runLog?.available ? "available" : "pending"}</span>
            </div>
            {logStreamWarning ? (
              <p className="mt-3 text-xs leading-6 text-amber-700">
                {logStreamWarning}
              </p>
            ) : null}
            <pre className="mt-3 max-h-80 min-w-0 overflow-auto whitespace-pre-wrap break-words text-xs leading-6 text-stone-700">
              {runLog?.available ? runLog.content : "日志尚未生成。"}
            </pre>
            {runLog?.truncated ? (
              <p className="mt-3 text-xs leading-6 text-stone-500">
                当前只显示尾部日志预览。
              </p>
            ) : null}
          </div>
          <p className="mt-2 text-sm leading-7 text-stone-500">
            当前版本已切到 SSE 事件流；若连接中断，会在下一次页面进入时重新拉取状态。
          </p>
        </div>
      </div>
    </section>
  );
}
