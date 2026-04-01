"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import {
  cleanRun,
  getRun,
  getRunLog,
  RunLogChunk,
  RunLogPreview,
  resumeRun,
  RunSession,
  subscribeRunEvents,
  subscribeRunLogEvents,
} from "@/lib/api/runs";
import type { RunWorkbenchPreview } from "@/lib/preview/workbench";
import { RunV2Sections } from "@/components/run/run-v2-sections";

export function RunSessionWorkbenchV2({
  preview,
}: {
  preview?: RunWorkbenchPreview | null;
}) {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const isPreview = !!preview;

  const [run, setRun] = useState<RunSession | null>(preview?.run ?? null);
  const [runLog, setRunLog] = useState<RunLogPreview | null>(preview?.runLog ?? null);
  const [error, setError] = useState<string | null>(null);
  const [streamWarning, setStreamWarning] = useState<string | null>(null);
  const [logStreamWarning, setLogStreamWarning] = useState<string | null>(null);
  const [actionState, setActionState] = useState<"idle" | "resuming" | "cleaning">("idle");

  useEffect(() => {
    if (preview) {
      return;
    }
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
  }, [preview, runId]);

  useEffect(() => {
    if (preview) {
      return;
    }
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
  }, [preview, runId, run?.status]);

  async function handleResume() {
    if (isPreview) {
      return;
    }
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
    if (isPreview) {
      return;
    }
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
  const previewResultsHref = `/courses/preview/results?mode=preview&scenario=${preview?.scenario === "completed" ? "completed" : "running"}&runId=preview-run`;
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
    <RunV2Sections
      run={run}
      runHeadline={runHeadline}
      runSummary={runSummary}
      statusTone={statusTone}
      streamWarning={streamWarning}
      logStreamWarning={logStreamWarning}
      runLog={runLog}
      canResume={canResume}
      canClean={canClean}
      actionState={actionState}
      previewScenario={preview?.scenario}
      previewResultsHref={previewResultsHref}
      isPreview={isPreview}
      onResume={() => void handleResume()}
      onClean={() => void handleClean()}
    />
  );
}
