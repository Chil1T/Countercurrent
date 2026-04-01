"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  getResultsSnapshot,
  getResultsSnapshotContent,
  getReviewSummary,
  type ArtifactContent,
  type ReviewSummary,
  type ResultsSnapshot,
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
  buildResultsSnapshotSelection,
  buildResultsSnapshotTree,
  findResultsTreeNodeBySelection,
  getResultsTreeSelectionAncestors,
  isArtifactTreeLoading,
  type ResultsTreeNode,
  type ResultsTreeSection,
} from "@/lib/results-view";
import type { ResultsWorkbenchPreview } from "@/lib/preview/workbench";
import { ResultsV2Sections } from "@/components/results/results-v2-sections";

function collectExpandableKeys(nodes: ResultsTreeNode[]): string[] {
  const keys: string[] = [];

  for (const node of nodes) {
    if ("children" in node) {
      keys.push(node.key);
      keys.push(...collectExpandableKeys(node.children));
    }
  }

  return keys;
}

function collectTreeSectionKeys(sections: ResultsTreeSection[]): string[] {
  const keys: string[] = [];

  for (const section of sections) {
    keys.push(section.key);
    keys.push(...collectExpandableKeys(section.children));
  }

  return keys;
}

function findFirstSelectableSelection(nodes: ResultsTreeNode[]): string | null {
  for (const node of nodes) {
    if ("path" in node) {
      return node.key;
    }
    const childSelection = findFirstSelectableSelection(node.children);
    if (childSelection) {
      return childSelection;
    }
  }

  return null;
}

function buildPreviewSnapshot(preview: ResultsWorkbenchPreview): ResultsSnapshot {
  const chapterFiles = preview.nodes
    .filter((node) => node.path.startsWith("chapters/") && node.path.endsWith(".md"))
    .map((node) => ({
      chapter_id: node.path.split("/")[1] ?? "chapter",
      file: node,
    }));
  const chapterMap = new Map<string, Array<{ path: string; kind: string; size: number }>>();
  for (const entry of chapterFiles) {
    const files = chapterMap.get(entry.chapter_id) ?? [];
    files.push(entry.file);
    chapterMap.set(entry.chapter_id, files);
  }

  return {
    current_course_id: preview.context?.course_id ?? "preview-course",
    current_course_runs: [
      {
        run_id: preview.run?.id ?? "preview-run",
        chapters: [...chapterMap.entries()].map(([chapterId, files]) => ({
          chapter_id: chapterId,
          files,
        })),
      },
    ],
    historical_courses: [],
  };
}

async function loadResultsSnapshot(courseId: string, runId?: string | null) {
  const [snapshot, summary, context, nextRun] = await Promise.all([
    getResultsSnapshot(courseId),
    getReviewSummary(courseId),
    getCourseResultsContext(courseId).catch(() => null),
    runId ? getRun(runId).catch(() => null) : Promise.resolve(null),
  ]);

  return { snapshot, summary, context, nextRun };
}

export function ResultsWorkbenchV2({
  courseId,
  runId,
  preview,
}: {
  courseId: string | null;
  runId?: string | null;
  preview?: ResultsWorkbenchPreview | null;
}) {
  const isPreview = !!preview;
  const initialPreviewSnapshot = preview ? buildPreviewSnapshot(preview) : null;
  const initialPreviewTree = initialPreviewSnapshot ? buildResultsSnapshotTree(initialPreviewSnapshot, preview?.run?.id ?? null) : [];
  const initialPreviewSelection = initialPreviewTree.length > 0 ? findFirstSelectableSelection(initialPreviewTree[0]?.children ?? []) ?? findFirstSelectableSelection(initialPreviewTree[1]?.children ?? []) : null;

  const [snapshot, setSnapshot] = useState<ResultsSnapshot | null>(initialPreviewSnapshot);
  const [run, setRun] = useState<RunSession | null>(preview?.run ?? null);
  const [context, setContext] = useState<CourseResultsContext | null>(preview?.context ?? null);
  const [selectedSelection, setSelectedSelection] = useState<string | null>(initialPreviewSelection);
  const [content, setContent] = useState<ArtifactContent | null>(
    initialPreviewSelection && preview
      ? (() => {
          const node = findResultsTreeNodeBySelection(initialPreviewTree, initialPreviewSelection);
          return node && "path" in node ? (preview.contentByPath[node.path] ?? null) : null;
        })()
      : null,
  );
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(preview?.reviewSummary ?? null);
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(
    () => new Set(isPreview ? collectTreeSectionKeys(initialPreviewTree) : ["historical-courses", "current-course"]),
  );
  const [error, setError] = useState<string | null>(null);
  const [exportCompletedOnly, setExportCompletedOnly] = useState(false);
  const [exportFinalOnly, setExportFinalOnly] = useState(false);
  const previousRunRef = useRef<RunSession | null>(null);

  useEffect(() => {
    if (preview || !courseId) {
      return;
    }
    let cancelled = false;

    async function refreshSnapshot() {
      setError(null);
      try {
        const { snapshot, summary, context, nextRun } = await loadResultsSnapshot(courseId, runId);
        if (cancelled) {
          return;
        }
        setSnapshot(snapshot);
        setReviewSummary(summary);
        setContext(context);
        setRun(nextRun);
        previousRunRef.current = nextRun;

        const nextTree = buildResultsSnapshotTree(snapshot, runId);
        const firstSelection =
          findFirstSelectableSelection(nextTree[0]?.children ?? []) ??
          findFirstSelectableSelection(nextTree[1]?.children ?? []) ??
          null;
        setSelectedSelection((current) => {
          if (!current) {
            return firstSelection;
          }
          return findResultsTreeNodeBySelection(nextTree, current) ? current : firstSelection;
        });
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      }
    }

    void refreshSnapshot();

    return () => {
      cancelled = true;
    };
  }, [courseId, preview, runId]);

  useEffect(() => {
    if (preview || !courseId || !runId) {
      return;
    }
    let cancelled = false;

    const unsubscribe = subscribeRunEvents(runId, {
      onUpdate: (nextRun) => {
        if (cancelled) {
          return;
        }

        if (shouldRefreshArtifactsOnRunUpdate(previousRunRef.current, nextRun)) {
          void loadResultsSnapshot(courseId, runId)
            .then(({ snapshot, summary, context }) => {
              if (cancelled) {
                return;
              }
              setSnapshot(snapshot);
              setReviewSummary(summary);
              setContext(context);
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
    if (!courseId || !selectedSelection) {
      return;
    }
    const selectedNode = findResultsTreeNodeBySelection(treeSections, selectedSelection);
    if (!selectedNode || !("path" in selectedNode)) {
      return;
    }
    if (preview) {
      setContent(preview.contentByPath[selectedNode.path] ?? null);
      return;
    }

    let cancelled = false;

    async function loadContent() {
      try {
        const nextContent = await getResultsSnapshotContent(courseId, {
          sourceCourseId: selectedNode.sourceCourseId === "__current__" ? null : selectedNode.sourceCourseId,
          runId: selectedNode.runId,
          path: selectedNode.path,
        });
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
  }, [courseId, preview, preview?.contentByPath, selectedSelection]);

  const treeSections = useMemo(
    () => buildResultsSnapshotTree(snapshot ?? { current_course_id: courseId ?? "unbound-course", current_course_runs: [], historical_courses: [] }, runId ?? null),
    [courseId, runId, snapshot],
  );
  const chapterStatusMap = useMemo(() => {
    const activeChapterProgress = context?.latest_run?.chapter_progress ?? [];
    return new Map(activeChapterProgress.map((chapter) => [chapter.chapter_id, chapter.status]));
  }, [context?.latest_run?.chapter_progress]);
  const loadingArtifacts = isPreview || !courseId ? false : isArtifactTreeLoading(context?.latest_run?.status);
  const previewContent = selectedSelection ? content : null;
  const exportCacheBust = useMemo(
    () => `${snapshot?.current_course_runs.length ?? 0}-${reviewSummary?.report_count ?? 0}-${reviewSummary?.issue_count ?? 0}`,
    [reviewSummary?.issue_count, reviewSummary?.report_count, snapshot?.current_course_runs.length],
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
      selectedSelection={selectedSelection}
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
      onSelectFile={(selection) => {
        setSelectedSelection(selection);
        setExpandedKeys((current) => {
          const next = new Set(current);
          for (const key of getResultsTreeSelectionAncestors(selection)) {
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
