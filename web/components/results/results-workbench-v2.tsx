"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  getArtifactContent,
  getArtifactTree,
  getReviewSummary,
  type ArtifactContent,
  type ArtifactNode,
  type ReviewSummary,
} from "@/lib/api/artifacts";
import {
  getCourseResultsContext,
  getRun,
  subscribeRunEvents,
  type CourseResultsContext,
  type RunSession,
} from "@/lib/api/runs";
import { shouldRefreshArtifactsOnRunUpdate } from "@/lib/results-refresh";
import {
  buildArtifactTree,
  findArtifactTreeNodeByPath,
  getArtifactTreePathAncestors,
  isArtifactTreeLoading,
  type ArtifactTreeNode,
} from "@/lib/results-view";
import type { ResultsWorkbenchPreview } from "@/lib/preview/workbench";
import { ResultsV2Sections } from "@/components/results/results-v2-sections";

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

function collectTreeSectionKeys(sections: ReturnType<typeof buildArtifactTree>): string[] {
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

async function loadArtifactSnapshot(courseId: string, runId?: string | null) {
  const [tree, summary, context, nextRun] = await Promise.all([
    getArtifactTree(courseId),
    getReviewSummary(courseId),
    getCourseResultsContext(courseId).catch(() => null),
    runId ? getRun(runId).catch(() => null) : Promise.resolve(null),
  ]);

  return { tree, summary, context, nextRun };
}

export function ResultsWorkbenchV2({
  courseId,
  runId,
  preview,
}: {
  courseId: string;
  runId?: string | null;
  preview?: ResultsWorkbenchPreview | null;
}) {
  const isPreview = !!preview;
  const initialPreviewTree = preview ? buildArtifactTree(preview.nodes) : [];
  const initialPreviewPath = preview ? (findFirstSelectablePath(initialPreviewTree) ?? null) : null;
  const [nodes, setNodes] = useState<ArtifactNode[]>(preview?.nodes ?? []);
  const [run, setRun] = useState<RunSession | null>(preview?.run ?? null);
  const [context, setContext] = useState<CourseResultsContext | null>(preview?.context ?? null);
  const [selectedPath, setSelectedPath] = useState<string | null>(initialPreviewPath);
  const [content, setContent] = useState<ArtifactContent | null>(
    initialPreviewPath && preview ? (preview.contentByPath[initialPreviewPath] ?? null) : null,
  );
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(
    preview?.reviewSummary ?? null,
  );
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(
    () => new Set(preview ? collectTreeSectionKeys(initialPreviewTree) : []),
  );
  const [error, setError] = useState<string | null>(null);
  const [exportCompletedOnly, setExportCompletedOnly] = useState(false);
  const [exportFinalOnly, setExportFinalOnly] = useState(false);
  const previousRunRef = useRef<RunSession | null>(null);

  useEffect(() => {
    if (preview) {
      return;
    }
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
          return findArtifactTreeNodeByPath(nextTree, current) ? current : firstPreviewable;
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
  }, [courseId, preview, runId]);

  useEffect(() => {
    if (preview || !runId) {
      return;
    }
    let cancelled = false;

    const unsubscribe = subscribeRunEvents(runId, {
      onUpdate: (nextRun) => {
        if (cancelled) {
          return;
        }

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
                return findArtifactTreeNodeByPath(nextTree, current) ? current : firstPreviewable;
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
      },
    });

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [courseId, preview, runId]);

  useEffect(() => {
    if (preview || !selectedPath) {
      return;
    }
    let cancelled = false;
    const path = selectedPath;

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
  }, [courseId, preview, selectedPath]);

  const treeSections = useMemo(() => buildArtifactTree(nodes), [nodes]);
  const chapterStatusMap = useMemo(() => {
    const activeChapterProgress = context?.latest_run?.chapter_progress ?? [];
    return new Map(activeChapterProgress.map((chapter) => [chapter.chapter_id, chapter.status]));
  }, [context?.latest_run?.chapter_progress]);
  const loadingArtifacts = isPreview ? false : isArtifactTreeLoading(context?.latest_run?.status);
  const previewContent = selectedPath
    ? isPreview
      ? (preview?.contentByPath[selectedPath] ?? null)
      : content
    : null;
  const exportCacheBust = useMemo(
    () => `${nodes.length}-${reviewSummary?.report_count ?? 0}-${reviewSummary?.issue_count ?? 0}`,
    [nodes.length, reviewSummary?.issue_count, reviewSummary?.report_count],
  );
  const scopedRunLabel = runId && run ? `Scoped view · ${run.id.slice(0, 8)} · ${run.status}` : null;
  const courseViewLabel = context?.latest_run ? "Course view · latest state" : null;

  if (error) {
    return (
      <div className="rounded-[28px] border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
        {error}
      </div>
    );
  }

  return (
    <ResultsV2Sections
      courseId={courseId}
      runId={runId}
      previewScenario={preview?.scenario}
      isPreview={isPreview}
      treeSections={treeSections}
      expandedKeys={expandedKeys}
      selectedPath={selectedPath}
      chapterStatusMap={chapterStatusMap}
      previewContent={previewContent}
      reviewSummary={reviewSummary}
      loadingArtifacts={loadingArtifacts}
      exportCompletedOnly={exportCompletedOnly}
      exportFinalOnly={exportFinalOnly}
      exportCacheBust={exportCacheBust}
      scopedRunLabel={scopedRunLabel}
      courseViewLabel={courseViewLabel}
      onToggleSection={(key) => {
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
          for (const key of getArtifactTreePathAncestors(path)) {
            next.add(key);
          }
          return next;
        });
      }}
      onExportCompletedOnlyChange={setExportCompletedOnly}
      onExportFinalOnlyChange={setExportFinalOnly}
    />
  );
}
