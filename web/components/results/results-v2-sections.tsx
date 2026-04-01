"use client";

import { ArtifactContent, ReviewSummary, buildExportUrl } from "@/lib/api/artifacts";
import {
  ResultsTreeNode,
  ResultsTreeSection,
  getArtifactDisplayName,
  getArtifactTreeCardClass,
} from "@/lib/results-view";
import { SurfaceCard } from "@/components/stitch-v2/surface-card";
import { StatusChip } from "@/components/stitch-v2/status-chip";

function TreeNode({
  node,
  depth,
  selectedSelection,
  expandedKeys,
  chapterStatusMap,
  onToggleFolder,
  onSelectFile,
}: {
  node: ResultsTreeNode;
  depth: number;
  selectedSelection: string | null;
  expandedKeys: Set<string>;
  chapterStatusMap?: Map<string, string>;
  onToggleFolder: (key: string) => void;
  onSelectFile: (selection: string) => void;
}) {
  const isFolder = "children" in node;
  const isActive = isFolder ? expandedKeys.has(node.key) : node.key === selectedSelection;
  const chapterStatus =
    isFolder && depth === 1 && chapterStatusMap?.has(node.label)
      ? chapterStatusMap.get(node.label)
      : null;

  return (
    <div className="min-w-0" style={{ paddingLeft: depth > 0 ? `${depth * 0.75}rem` : 0 }}>
      <button
        type="button"
        onClick={() => {
          if (isFolder) {
            onToggleFolder(node.key);
            return;
          }
          onSelectFile(node.key);
        }}
        className={`flex w-full min-w-0 items-center justify-between gap-3 overflow-hidden rounded-2xl px-4 py-3 text-left transition ${getArtifactTreeCardClass(
          node.key,
          isActive,
        )}`}
      >
        <span className="flex min-w-0 items-center gap-2 truncate">
          <span className="truncate font-medium">{node.label}</span>
          {chapterStatus ? (
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider ${
                chapterStatus === "completed"
                  ? "bg-emerald-100 text-emerald-700"
                  : chapterStatus === "running"
                    ? "bg-amber-100 text-amber-700"
                    : chapterStatus === "failed"
                      ? "bg-rose-100 text-rose-700"
                      : "bg-stone-200 text-stone-600"
              }`}
            >
              {chapterStatus}
            </span>
          ) : null}
        </span>
        <span className="shrink-0 text-xs uppercase tracking-[0.18em]">
          {isFolder ? (isActive ? "收起" : "展开") : "文件"}
        </span>
      </button>
      {isFolder && isActive ? (
        <div className="mt-2 space-y-2">
          {node.children.map((child) => (
            <TreeNode
              key={child.key}
              node={child}
              depth={depth + 1}
              selectedSelection={selectedSelection}
              expandedKeys={expandedKeys}
              chapterStatusMap={chapterStatusMap}
              onToggleFolder={onToggleFolder}
              onSelectFile={onSelectFile}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function ResultsV2Sections({
  courseId,
  runId,
  previewScenario,
  isPreview,
  treeSections,
  expandedKeys,
  selectedSelection,
  chapterStatusMap,
  previewContent,
  reviewSummary,
  loadingArtifacts,
  exportCompletedOnly,
  exportFinalOnly,
  exportCacheBust,
  scopedRunLabel,
  courseViewLabel,
  onToggleSection,
  onToggleFolder,
  onSelectFile,
  onExportCompletedOnlyChange,
  onExportFinalOnlyChange,
}: {
  courseId: string | null;
  runId?: string | null;
  previewScenario?: string;
  isPreview: boolean;
  treeSections: ResultsTreeSection[];
  expandedKeys: Set<string>;
  selectedSelection: string | null;
  chapterStatusMap: Map<string, string>;
  previewContent: ArtifactContent | null;
  reviewSummary: ReviewSummary | null;
  loadingArtifacts: boolean;
  exportCompletedOnly: boolean;
  exportFinalOnly: boolean;
  exportCacheBust: string;
  scopedRunLabel: string | null;
  courseViewLabel: string | null;
  onToggleSection: (key: string) => void;
  onToggleFolder: (key: string) => void;
  onSelectFile: (selection: string) => void;
  onExportCompletedOnlyChange: (checked: boolean) => void;
  onExportFinalOnlyChange: (checked: boolean) => void;
}) {
  return (
    <section className="space-y-6">
      <SurfaceCard className="overflow-hidden p-6 md:p-7 xl:p-8">
        <div className="grid gap-8 xl:grid-cols-[1.12fr_0.88fr]">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <StatusChip label="Results Control Center" tone="accent" />
              <StatusChip label="Course Latest View" />
              {runId ? <StatusChip label="当前 run 已附着" tone="muted" /> : null}
            </div>
            <h3 className="font-stitch-headline mt-5 text-4xl font-black tracking-[-0.05em] text-stone-900 md:text-5xl">
              结果树现在按课程与 run 快照组织，只显示最终 Markdown 产物。
            </h3>
            <p className="mt-5 max-w-3xl text-sm leading-8 text-stone-600 md:text-base">
              过去课程与当前课程分层展示，当前课程内部按 run 和章节展开；当前 run 只做标记，不再把 intermediate 或 runtime 文件混进主树。
            </p>
            <p className="mt-2 text-xs uppercase tracking-[0.18em] text-stone-400">
              过去课程产物 / 当前课程产物 / 当前 run
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              {scopedRunLabel ? <StatusChip label={scopedRunLabel} tone="muted" /> : null}
              {courseViewLabel ? <StatusChip label={courseViewLabel} /> : null}
              {loadingArtifacts ? <StatusChip label="文件仍在生成中" tone="accent" /> : null}
            </div>
          </div>

          <SurfaceCard tone="rail" className="p-5 md:p-6">
            <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-white/55">
              Reviewer / Export
            </p>
            <h4 className="font-stitch-headline mt-4 text-3xl font-black tracking-[-0.05em] text-white">
              输出把关
            </h4>
            <div className="mt-5 grid gap-4 text-sm leading-7 text-stone-300">
              <div>
                报告数：{reviewSummary?.report_count ?? 0} / 问题数：{reviewSummary?.issue_count ?? 0}
              </div>
              <div className="grid gap-2">
                {(reviewSummary?.reports ?? []).map((report) => (
                  <div
                    key={report.path}
                    className="rounded-[1.2rem] border border-white/10 bg-white/5 px-4 py-3"
                  >
                    <div className="font-medium text-stone-100">{report.path}</div>
                    <div className="mt-1 text-xs uppercase tracking-[0.16em] text-stone-400">
                      {report.status}
                    </div>
                  </div>
                ))}
              </div>
              {isPreview ? (
                <div className="rounded-[1.2rem] border border-sky-200/30 bg-sky-50/10 px-4 py-3 text-sm text-sky-100">
                  <span className="font-semibold uppercase tracking-[0.18em]">Preview</span>
                  <span className="ml-2">当前为 {previewScenario} 示例态。</span>
                </div>
              ) : null}
            </div>
          </SurfaceCard>
        </div>
      </SurfaceCard>

      <div className="grid gap-6 xl:grid-cols-[minmax(260px,0.9fr)_minmax(0,1.1fr)]">
        <div className="grid min-w-0 gap-6 xl:sticky xl:top-24 xl:h-[calc(100vh-8.5rem)] xl:grid-rows-[minmax(0,1fr)_auto]">
          <SurfaceCard className="flex min-h-0 flex-col p-5 md:p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-[var(--stitch-shell-primary-strong)]">
                  Snapshot Tree
                </p>
                <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-stone-900">
                  文件树
                </h4>
              </div>
              <StatusChip label={`${treeSections.length} sections`} tone="accent" />
            </div>

            <div className="mt-5 flex-1 overflow-x-hidden overflow-y-auto pr-1 text-sm text-stone-700">
              {treeSections.map((section) => {
                const sectionExpanded = expandedKeys.has(section.key);

                return (
                  <div
                    key={section.key}
                    className="mb-4 min-w-0 rounded-[22px] border border-[var(--stitch-shell-border)] bg-[var(--stitch-shell-panel-soft)] p-3 last:mb-0"
                  >
                    <button
                      type="button"
                      onClick={() => onToggleSection(section.key)}
                      className={`flex w-full min-w-0 items-center justify-between gap-3 overflow-hidden rounded-2xl px-4 py-3 text-left transition ${getArtifactTreeCardClass(
                        section.key,
                        sectionExpanded,
                      )}`}
                    >
                      <span className="font-semibold">{section.label}</span>
                      <span className="shrink-0 text-xs uppercase tracking-[0.18em]">
                        {sectionExpanded ? "收起" : "展开"}
                      </span>
                    </button>
                    {sectionExpanded ? (
                      <div className="mt-2 space-y-2">
                        {section.children.length > 0 ? (
                          section.children.map((node) => (
                            <TreeNode
                              key={node.key}
                              node={node}
                              depth={0}
                              selectedSelection={selectedSelection}
                              expandedKeys={expandedKeys}
                              chapterStatusMap={chapterStatusMap}
                              onToggleFolder={onToggleFolder}
                              onSelectFile={onSelectFile}
                            />
                          ))
                        ) : (
                          <div className="rounded-2xl border border-dashed border-stone-200 px-4 py-3 text-xs text-stone-500">
                            暂无文件
                          </div>
                        )}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </SurfaceCard>

          <SurfaceCard tone="rail" className="p-5 md:p-6">
            <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-white/55">
              Export Filters
            </p>
            <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-white">
              过滤导出
            </h4>
            <div className="mt-5 grid gap-3 text-sm text-stone-300">
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={exportCompletedOnly}
                  onChange={(event) => onExportCompletedOnlyChange(event.target.checked)}
                  disabled={isPreview}
                  className="rounded border-stone-600 bg-[var(--stitch-shell-rail)] text-stone-900 focus:ring-stone-400 focus:ring-offset-[var(--stitch-shell-rail)]"
                />
                <span className="select-none">只导出已完成章节</span>
              </label>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={exportFinalOnly}
                  onChange={(event) => onExportFinalOnlyChange(event.target.checked)}
                  disabled={isPreview}
                  className="rounded border-stone-600 bg-[var(--stitch-shell-rail)] text-stone-900 focus:ring-stone-400 focus:ring-offset-[var(--stitch-shell-rail)]"
                />
                <span className="select-none">仅导出最终产物</span>
              </label>
            </div>
            <div className="mt-5">
              {isPreview || !courseId ? (
                <button
                  type="button"
                  disabled
                  className="inline-flex cursor-not-allowed rounded-full bg-stone-300 px-5 py-3 text-sm font-semibold text-stone-700"
                >
                  导出 ZIP
                </button>
              ) : (
                <a
                  href={buildExportUrl(courseId, {
                    cacheBust: exportCacheBust,
                    completedChaptersOnly: exportCompletedOnly,
                    finalOutputsOnly: exportFinalOnly,
                  })}
                  className="inline-flex rounded-full bg-white px-5 py-3 text-sm font-semibold text-stone-900 transition hover:bg-stone-200"
                >
                  导出 ZIP
                </a>
              )}
              {isPreview ? (
                <div className="mt-2 text-xs uppercase tracking-[0.18em] text-stone-400">
                  Preview only
                </div>
              ) : null}
            </div>
          </SurfaceCard>
        </div>

        <SurfaceCard className="overflow-hidden xl:sticky xl:top-24 xl:self-start">
          <div className="flex h-full min-h-[30rem] flex-col xl:h-[calc(100vh-8.5rem)]">
            <div className="sticky top-0 z-10 border-b border-[var(--stitch-shell-border)] bg-[var(--stitch-shell-panel)]">
              <div className="px-6 pb-5 pt-6">
                <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-[var(--stitch-shell-primary-strong)]">
                  Artifact Preview
                </p>
                <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-stone-900">
                  文件预览
                </h4>
                <div className="mt-4 text-sm font-medium text-stone-700">
                  {previewContent ? getArtifactDisplayName(previewContent.path) : "请选择文件"}
                </div>
                <div className="mt-1 truncate text-xs leading-6 text-stone-500">
                  {previewContent?.path ?? (courseId ? "当前仅展示 Markdown 快照路径" : "等待课程上下文后显示路径")}
                </div>
              </div>
            </div>
            <div className="min-h-0 flex-1 overflow-auto p-6 pt-5">
              <pre className="min-h-full whitespace-pre-wrap break-words rounded-2xl border border-[var(--stitch-shell-border)] bg-[var(--stitch-shell-panel-soft)] p-5 text-sm leading-7 text-stone-700">
                {previewContent?.content ?? "暂无预览内容"}
              </pre>
            </div>
          </div>
        </SurfaceCard>
      </div>
    </section>
  );
}
