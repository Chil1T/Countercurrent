"use client";

import { useEffect, useMemo, useState } from "react";

import {
  buildExportUrl,
  getArtifactContent,
  getArtifactTree,
  getReviewSummary,
  type ArtifactContent,
  type ArtifactNode,
  type ReviewSummary,
} from "@/lib/api/artifacts";
import { getRun, subscribeRunEvents, type RunSession } from "@/lib/api/runs";
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

function TreeNode({
  node,
  depth,
  selectedPath,
  expandedKeys,
  onToggleFolder,
  onSelectFile,
}: {
  node: ArtifactTreeNode;
  depth: number;
  selectedPath: string | null;
  expandedKeys: Set<string>;
  onToggleFolder: (key: string) => void;
  onSelectFile: (path: string) => void;
}) {
  const isFolder = "children" in node;
  const isActive = isFolder ? expandedKeys.has(node.key) : node.path === selectedPath;

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
        <span className="min-w-0 truncate font-medium">{node.label}</span>
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
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [content, setContent] = useState<ArtifactContent | null>(null);
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(() => new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadArtifacts() {
      setError(null);
      try {
        const [tree, summary, nextRun] = await Promise.all([
          getArtifactTree(courseId),
          getReviewSummary(courseId),
          runId ? getRun(runId).catch(() => null) : Promise.resolve(null),
        ]);
        if (cancelled) {
          return;
        }
        setNodes(tree.nodes);
        setReviewSummary(summary);
        setRun(nextRun);

        const nextTree = buildArtifactTree(tree.nodes);
        const firstPreviewable = findFirstSelectablePath(nextTree) ?? null;
        const nextExpandedKeys = new Set(collectTreeSectionKeys(nextTree));
        setExpandedKeys(nextExpandedKeys);
        setSelectedPath(firstPreviewable);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      }
    }

    void loadArtifacts();

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
          setRun(nextRun);
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
    <section className="grid min-h-[calc(100vh-12rem)] gap-5 xl:grid-cols-[minmax(250px,300px)_minmax(0,1fr)]">
      <div className="min-w-0 grid gap-5 xl:sticky xl:top-24 xl:self-start">
        <div className="min-h-0 rounded-[28px] border border-stone-200 bg-stone-50 p-5">
          <h3 className="text-lg font-semibold">文件树</h3>
          {loadingArtifacts ? (
            <div className="mt-4 rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-700">
              文件仍在生成中，完成后会自动出现在这里。
            </div>
          ) : null}
          <div className="mt-4 h-[26rem] overflow-x-hidden overflow-y-auto pr-1 text-sm text-stone-700">
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
            <div>
              <a
                href={buildExportUrl(courseId, exportCacheBust)}
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
