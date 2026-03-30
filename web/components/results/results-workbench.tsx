"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  buildExportUrl,
  getArtifactContent,
  getArtifactTree,
  getReviewSummary,
  type ArtifactContent,
  type ArtifactNode,
  type ReviewSummary,
} from "@/lib/api/artifacts";
import { getRun, getCourseResultsContext, subscribeRunEvents, type RunSession, type CourseResultsContext } from "@/lib/api/runs";
import { shouldRefreshArtifactsOnRunUpdate } from "@/lib/results-refresh";
import {
  getArtifactDisplayName,
  getArtifactTreeCardClass,
  buildArtifactTree,
  isArtifactTreeLoading,
  type ArtifactTreeNode,
  type ArtifactTreeSection,
} from "@/lib/results-view";

function collectExpandableKeys(nodes: ArtifactTreeNode[]): string[] {
  const keys: string[] = [];

  for (const node of nodes) {
    if ("children" in node) {
      keys.push(node.key);
      keys.push(...collectExpandableKeys(node.children));
    }
  }

  return keys;
}

function collectTreeSectionKeys(sections: ArtifactTreeSection[]): string[] {
  const keys: string[] = [];
  for (const section of sections) {
    keys.push(section.key);
    keys.push(...collectExpandableKeys(section.children));
  }
  return keys;
}

function findFirstSelectablePath(nodes: ArtifactTreeNode[]): string | null {
  for (const node of nodes) {
    if ("path" in node) {
      return node.path;
    }
    const childPath = findFirstSelectablePath(node.children);
    if (childPath) {
      return childPath;
    }
  }

  return null;
}

function getTreePathAncestors(path: string): string[] {
  if (path.startsWith("chapters/")) {
    const segments = path.split("/");
    const chapterId = segments[1] ?? "chapter";
    const bucket = segments[2] === "intermediate" ? "intermediate" : "final";
    return ["chapter", chapterId, `${chapterId}:${bucket}`];
  }

  if (path.startsWith("global/")) {
    return ["global"];
  }

  return ["runtime"];
}

async function loadArtifactSnapshot(courseId: string, runId?: string | null) {
  const [tree, summary, context, nextRun] = await Promise.all([
    getArtifactTree(courseId),
    getReviewSummary(courseId),
    getCourseResultsContext(courseId).catch(() => null),
    runId ? getRun(runId).catch(() => null) : Promise.resolve(null),
  ]);
  return { tree, summary, context, nextRun };
}

function TreeNode({
  node,
  depth,
  selectedPath,
  expandedKeys,
  chapterStatusMap,
  onToggleFolder,
  onSelectFile,
}: {
  node: ArtifactTreeNode;
  depth: number;
  selectedPath: string | null;
  expandedKeys: Set<string>;
  chapterStatusMap?: Map<string, string>;
  onToggleFolder: (key: string) => void;
  onSelectFile: (path: string) => void;
}) {
  const isFolder = "children" in node;
  const isActive = isFolder ? expandedKeys.has(node.key) : node.path === selectedPath;
  const chapterStatus = isFolder && depth === 0 && chapterStatusMap?.has(node.key) ? chapterStatusMap.get(node.key) : null;

  return (
    <div className="min-w-0" style={{ paddingLeft: depth > 0 ? `${depth * 0.75}rem` : 0 }}>
      <button
        type="button"
        onClick={() => {
          if (isFolder) {
            onToggleFolder(node.key);
            return;
          }
          onSelectFile(node.path);
        }}
        className={`flex min-w-0 w-full items-center justify-between gap-3 overflow-hidden rounded-2xl px-4 py-3 text-left transition ${getArtifactTreeCardClass(
          node.key,
          isActive,
        )}`}
      >
        <span className="min-w-0 flex items-center gap-2 truncate">
          <span className="truncate font-medium">{node.label}</span>
          {chapterStatus && (
            <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider ${
              chapterStatus === "completed" ? "bg-emerald-100 text-emerald-700" :
              chapterStatus === "running" ? "bg-amber-100 text-amber-700" :
              chapterStatus === "failed" ? "bg-rose-100 text-rose-700" :
              "bg-stone-200 text-stone-600"
            }`}>
              {chapterStatus}
            </span>
          )}
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
              selectedPath={selectedPath}
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

export function ResultsWorkbench({ courseId, runId }: { courseId: string; runId?: string | null }) {
  const [nodes, setNodes] = useState<ArtifactNode[]>([]);
  const [run, setRun] = useState<RunSession | null>(null);
  const [context, setContext] = useState<CourseResultsContext | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [content, setContent] = useState<ArtifactContent | null>(null);
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(() => new Set());
  const [error, setError] = useState<string | null>(null);
  const [exportCompletedOnly, setExportCompletedOnly] = useState(true);
  const [exportFinalOnly, setExportFinalOnly] = useState(true);
  const previousRunRef = useRef<RunSession | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function refreshArtifacts(preserveSelection: boolean) {
      setError(null);
      try {
        const { tree, summary, context, nextRun } = await loadArtifactSnapshot(courseId, runId);
        if (cancelled) {
          return;
        }
        setNodes(tree.nodes);
        setReviewSummary(summary);
        setContext(context);
        setRun(nextRun);
        previousRunRef.current = nextRun;

        const nextTree = buildArtifactTree(tree.nodes);
        const firstPreviewable = findFirstSelectablePath(nextTree) ?? null;
        const nextExpandedKeys = new Set(collectTreeSectionKeys(nextTree));
        setExpandedKeys((current) => {
          if (!preserveSelection) {
            return nextExpandedKeys;
          }
          return new Set([...current, ...nextExpandedKeys]);
        });
        setSelectedPath((current) => {
          if (!preserveSelection || !current) {
            return firstPreviewable;
          }
          return findNodeByPath(nextTree, current) ? current : firstPreviewable;
        });
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      }
    }

    void refreshArtifacts(false);

    return () => {
      cancelled = true;
    };
  }, [courseId, runId]);

  useEffect(() => {
    let cancelled = false;
    if (!runId) {
      return () => {
        cancelled = true;
      };
    }

    const unsubscribe = subscribeRunEvents(runId, {
      onUpdate: (nextRun) => {
        if (!cancelled) {
          if (shouldRefreshArtifactsOnRunUpdate(previousRunRef.current, nextRun)) {
            void loadArtifactSnapshot(courseId, runId)
              .then(({ tree, summary, context }) => {
                if (cancelled) {
                  return;
                }
                setNodes(tree.nodes);
                setReviewSummary(summary);
                setContext(context);

                const nextTree = buildArtifactTree(tree.nodes);
                const firstPreviewable = findFirstSelectablePath(nextTree) ?? null;
                setSelectedPath((current) => {
                  if (!current) {
                    return firstPreviewable;
                  }
                  return findNodeByPath(nextTree, current) ? current : firstPreviewable;
                });
              })
              .catch((loadError) => {
                if (!cancelled) {
                  setError(loadError instanceof Error ? loadError.message : "Unknown error");
                }
              });
          }
          setRun(nextRun);
          previousRunRef.current = nextRun;
        }
      },
    });

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [courseId, runId]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedPath) {
      return;
    }
    const path: string = selectedPath;

    async function loadContent() {
      try {
        const nextContent = await getArtifactContent(courseId, path);
        if (!cancelled) {
          setContent(nextContent);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      }
    }

    void loadContent();

    return () => {
      cancelled = true;
    };
  }, [courseId, selectedPath]);

  const treeSections = useMemo(() => buildArtifactTree(nodes), [nodes]);
  const chapterStatusMap = useMemo(() => {
    const activeChapterProgress = run?.chapter_progress ?? context?.latest_run?.chapter_progress ?? [];
    return new Map(activeChapterProgress.map((c) => [c.chapter_id, c.status]));
  }, [run?.chapter_progress, context?.latest_run?.chapter_progress]);
  const loadingArtifacts = isArtifactTreeLoading(run?.status);
  const previewContent = selectedPath ? content : null;
  const exportCacheBust = useMemo(
    () => `${nodes.length}-${reviewSummary?.report_count ?? 0}-${reviewSummary?.issue_count ?? 0}`,
    [nodes.length, reviewSummary?.issue_count, reviewSummary?.report_count],
  );

  if (error) {
    return (
      <div className="rounded-[28px] border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
        {error}
      </div>
    );
  }

  return (
    <section className="grid min-h-[calc(100vh-12rem)] gap-5 xl:grid-cols-[minmax(250px,350px)_minmax(0,1fr)]">
      <div className="min-w-0 grid gap-5 xl:sticky xl:top-24 xl:h-[calc(100vh-8.5rem)] xl:grid-rows-[minmax(0,1fr)_auto]">
        <div className="flex min-h-0 flex-col rounded-[28px] border border-stone-200 bg-stone-50 p-5">
          <h3 className="shrink-0 text-lg font-semibold">文件树</h3>
          {runId && run ? (
            <div className="mt-4 rounded-xl border border-stone-200 bg-stone-100 px-4 py-2.5 text-xs text-stone-600">
              <span className="font-medium text-stone-800">Scoped view</span>: Viewing Run {run.id.slice(0, 8)} ({run.status})
            </div>
          ) : context?.latest_run ? (
            <div className="mt-4 rounded-xl border border-stone-200 bg-emerald-50/50 px-4 py-2.5 text-xs text-stone-600">
              <span className="font-medium text-emerald-800">Course view</span>: Showing latest state
            </div>
          ) : null}
          {loadingArtifacts ? (
            <div className="mt-4 rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-700">
              文件仍在生成中，完成后会自动出现在这里。
            </div>
          ) : null}
          <div className="mt-4 flex-1 overflow-x-hidden overflow-y-auto pr-1 text-sm text-stone-700">
            {treeSections.map((section) => {
              const sectionExpanded = expandedKeys.has(section.key);

              return (
                <div key={section.key} className="mb-4 min-w-0 rounded-[22px] border border-stone-200 bg-white p-3 last:mb-0">
                  <button
                    type="button"
                    onClick={() => {
                      setExpandedKeys((current) => {
                        const next = new Set(current);
                        if (next.has(section.key)) {
                          next.delete(section.key);
                        } else {
                          next.add(section.key);
                        }
                        return next;
                      });
                    }}
                    className={`flex min-w-0 w-full items-center justify-between gap-3 overflow-hidden rounded-2xl px-4 py-3 text-left transition ${getArtifactTreeCardClass(
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
                            selectedPath={selectedPath}
                            expandedKeys={expandedKeys}
                            chapterStatusMap={chapterStatusMap}
                            onToggleFolder={(key) => {
                              setExpandedKeys((current) => {
                                const next = new Set(current);
                                if (next.has(key)) {
                                  next.delete(key);
                                } else {
                                  next.add(key);
                                }
                                return next;
                              });
                            }}
                            onSelectFile={(path) => {
                              setSelectedPath(path);
                              setExpandedKeys((current) => {
                                const next = new Set(current);
                                for (const key of getTreePathAncestors(path)) {
                                  next.add(key);
                                }
                                return next;
                              });
                            }}
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
        </div>

        <div className="rounded-[28px] border border-stone-200 bg-[#15120f] p-5 text-stone-100">
          <h3 className="text-lg font-semibold">Reviewer / Export</h3>
          <div className="mt-4 grid gap-4 text-sm leading-7 text-stone-300">
            <div className="grid gap-4">
              <div className="font-medium text-stone-100">review 摘要</div>
              <div>
                报告数：{reviewSummary?.report_count ?? 0} / 问题数：{reviewSummary?.issue_count ?? 0}
              </div>
              <div>
                <div className="font-medium text-stone-100">review reports</div>
                <ul className="mt-1 list-disc pl-5">
                  {(reviewSummary?.reports ?? []).map((report) => (
                    <li key={report.path}>
                      {report.path} · {report.status}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="grid gap-3 pt-2">
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={exportCompletedOnly}
                  onChange={(e) => setExportCompletedOnly(e.target.checked)}
                  className="rounded border-stone-600 bg-[#15120f] text-stone-900 focus:ring-stone-400 focus:ring-offset-[#15120f]"
                />
                <span className="select-none text-sm">只导出已完成章节</span>
              </label>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={exportFinalOnly}
                  onChange={(e) => setExportFinalOnly(e.target.checked)}
                  className="rounded border-stone-600 bg-[#15120f] text-stone-900 focus:ring-stone-400 focus:ring-offset-[#15120f]"
                />
                <span className="select-none text-sm">仅导出最终产物 (排除中间数据)</span>
              </label>
            </div>
            <div className="pt-2">
              <a
                href={buildExportUrl(courseId, {
                  cacheBust: exportCacheBust,
                  completedChaptersOnly: exportCompletedOnly,
                  finalOutputsOnly: exportFinalOnly,
                })}
                className="inline-flex rounded-full bg-white px-5 py-3 text-sm font-medium text-stone-900 transition hover:bg-stone-200"
              >
                导出 ZIP
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="min-w-0 rounded-[28px] border border-stone-200 bg-white xl:sticky xl:top-24 xl:self-start">
        <div className="overflow-hidden rounded-[28px] xl:flex xl:h-[calc(100vh-8.5rem)] xl:flex-col">
          <div className="sticky top-0 z-10 border-b border-stone-200 bg-white">
            <div className="px-6 pt-6 pb-5">
              <h3 className="text-xl font-semibold">文件预览</h3>
              <div className="mt-3 text-sm font-medium text-stone-700">
                {previewContent ? getArtifactDisplayName(previewContent.path) : "请选择文件"}
              </div>
              <div className="mt-1 truncate text-xs leading-6 text-stone-500">
                {previewContent?.path ?? "路径会显示在这里"}
              </div>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-auto p-6 pt-5">
            <pre className="min-h-full min-w-0 whitespace-pre-wrap break-words rounded-2xl border border-stone-200 bg-stone-50 p-5 text-sm leading-7 text-stone-700">
              {previewContent?.content ?? "暂无预览内容"}
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}

function findNodeByPath(nodes: ArtifactTreeNode[], path: string): ArtifactTreeNode | null {
  for (const node of nodes) {
    if ("path" in node && node.path === path) {
      return node;
    }
    if ("children" in node) {
      const child = findNodeByPath(node.children, path);
      if (child) {
        return child;
      }
    }
  }
  return null;
}
