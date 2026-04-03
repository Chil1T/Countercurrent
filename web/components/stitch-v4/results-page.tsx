"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  buildExportUrl,
  getGlobalResultsSnapshot,
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
  buildResultsSnapshotTree,
  findResultsTreeNodeBySelection,
  getResultsTreeSelectionAncestors,
  isArtifactTreeLoading,
  type ResultsTreeNode,
  type ResultsTreeSection,
} from "@/lib/results-view";
import { StitchV4ContextRail } from "@/components/stitch-v4/context-rail";
import { StitchV4RightRail, StitchV4TopNav } from "@/components/stitch-v4/chrome";
import { StitchV4MaterialSymbol } from "@/components/stitch-v4/material-symbol";
import { useLocale } from "@/lib/locale";
import type { ProductContext } from "@/lib/product-nav";
import type { ResultsWorkbenchPreview } from "@/lib/preview/workbench";

function buildPreviewSnapshot(preview: ResultsWorkbenchPreview): ResultsSnapshot {
  return {
    current_course_id: preview.courseId,
    current_course_runs: [
      {
        run_id: preview.runId ?? "preview-run",
        chapters: [
          {
            chapter_id: "chapter-01",
            files: Object.values(preview.contentByPath)
              .filter((item) => item.path.endsWith(".md"))
              .map((item) => ({ path: item.path, kind: item.kind, size: item.content.length })),
          },
        ],
      },
    ],
    historical_courses: [],
  };
}

function collectFolderKeys(nodes: ResultsTreeNode[]): string[] {
  const keys: string[] = [];
  for (const node of nodes) {
    if ("children" in node) {
      keys.push(node.key, ...collectFolderKeys(node.children));
    }
  }
  return keys;
}

function firstSelection(sections: ResultsTreeSection[]): string | null {
  for (const section of sections) {
    const found = findFirstSelectableNode(section.children);
    if (found) {
      return found;
    }
  }
  return null;
}

function findFirstSelectableNode(nodes: ResultsTreeNode[]): string | null {
  for (const node of nodes) {
    if ("path" in node) {
      return node.key;
    }
    const child = findFirstSelectableNode(node.children);
    if (child) {
      return child;
    }
  }
  return null;
}

export function StitchV4ResultsPage({
  courseId,
  runId = null,
  preview = null,
  context: routeContext,
}: {
  courseId: string | null;
  runId?: string | null;
  preview?: ResultsWorkbenchPreview | null;
  context: ProductContext;
}) {
  const { messages, locale } = useLocale();
  const isPreview = !!preview;
  const previewSnapshot = preview ? buildPreviewSnapshot(preview) : null;
  const previewTree = useMemo(
    () =>
      previewSnapshot ? buildResultsSnapshotTree(previewSnapshot, preview?.runId ?? null, locale) : [],
    [locale, preview, previewSnapshot],
  );
  const previewSelection = useMemo(() => firstSelection(previewTree), [previewTree]);
  const previewExpandedKeys = useMemo(
    () =>
      new Set([
        "historical-courses",
        "current-course",
        ...collectFolderKeys(previewTree.flatMap((section) => section.children)),
      ]),
    [previewTree],
  );
  const previewContent = useMemo(() => {
    if (!preview || !previewSelection) {
      return null;
    }
    const node = findResultsTreeNodeBySelection(previewTree, previewSelection);
    return node && "path" in node ? (preview.contentByPath[node.path] ?? null) : null;
  }, [preview, previewSelection, previewTree]);

  const [snapshot, setSnapshot] = useState<ResultsSnapshot | null>(previewSnapshot);
  const [context, setContext] = useState<CourseResultsContext | null>(preview?.context ?? null);
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(preview?.reviewSummary ?? null);
  const [selectedSelection, setSelectedSelection] = useState<string | null>(previewSelection);
  const [content, setContent] = useState<ArtifactContent | null>(previewContent);
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(
    preview ? previewExpandedKeys : new Set(["historical-courses", "current-course"]),
  );
  const [error, setError] = useState<string | null>(null);
  const [exportCompletedOnly, setExportCompletedOnly] = useState(false);
  const [exportFinalOnly, setExportFinalOnly] = useState(false);
  const previousRunRef = useRef<RunSession | null>(null);
  const effectiveCourseId = courseId ?? snapshot?.current_course_id ?? routeContext.courseId ?? null;

  const treeSections = useMemo(
    () =>
      buildResultsSnapshotTree(
        snapshot ?? {
          current_course_id: effectiveCourseId,
          current_course_runs: [],
          historical_courses: [],
        },
        runId,
        locale,
      ),
    [effectiveCourseId, locale, runId, snapshot],
  );

  useEffect(() => {
    if (preview) {
      return;
    }

    let cancelled = false;

    async function loadPage() {
      try {
        const nextSnapshot = courseId
          ? await getResultsSnapshot(courseId)
          : await getGlobalResultsSnapshot();
        const activeCourseId = courseId ?? nextSnapshot.current_course_id;
        const [nextSummary, nextContext, nextRun] = await Promise.all([
          activeCourseId ? getReviewSummary(activeCourseId).catch(() => null) : Promise.resolve(null),
          activeCourseId ? getCourseResultsContext(activeCourseId).catch(() => null) : Promise.resolve(null),
          runId ? getRun(runId).catch(() => null) : Promise.resolve(null),
        ]);
        if (cancelled) {
          return;
        }
        setSnapshot(nextSnapshot);
        setReviewSummary(nextSummary);
        setContext(nextContext);
        previousRunRef.current = nextRun;
        const nextTree = buildResultsSnapshotTree(nextSnapshot, runId, locale);
        const selection = firstSelection(nextTree);
        setSelectedSelection((current) =>
          current && findResultsTreeNodeBySelection(nextTree, current) ? current : selection,
        );
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      }
    }

    void loadPage();
    return () => {
      cancelled = true;
    };
  }, [courseId, locale, preview, routeContext.courseId, runId]);

  useEffect(() => {
    if (preview || !effectiveCourseId || !runId) {
      return;
    }
    let cancelled = false;
    const activeCourseId = effectiveCourseId;
    const unsubscribe = subscribeRunEvents(runId, {
      onUpdate: (nextRun) => {
        if (cancelled) {
          return;
        }
        if (shouldRefreshArtifactsOnRunUpdate(previousRunRef.current, nextRun)) {
          void Promise.all([
            getResultsSnapshot(activeCourseId),
            getReviewSummary(activeCourseId),
            getCourseResultsContext(activeCourseId).catch(() => null),
          ]).then(([nextSnapshot, nextSummary, nextContext]) => {
            if (!cancelled) {
              setSnapshot(nextSnapshot);
              setReviewSummary(nextSummary);
              setContext(nextContext);
            }
          });
        }
        previousRunRef.current = nextRun;
      },
    });

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [effectiveCourseId, preview, runId]);

  useEffect(() => {
    if (!effectiveCourseId || !selectedSelection || preview) {
      return;
    }
    const node = findResultsTreeNodeBySelection(treeSections, selectedSelection);
    if (!node || !("path" in node)) {
      return;
    }
    let cancelled = false;
    void getResultsSnapshotContent(effectiveCourseId, {
      sourceCourseId: node.sourceCourseId === "__current__" ? null : node.sourceCourseId,
      runId: node.runId,
      path: node.path,
    })
      .then((nextContent) => {
        if (!cancelled) {
          setContent(nextContent);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [effectiveCourseId, preview, selectedSelection, treeSections]);

  const selectedNode = selectedSelection
    ? findResultsTreeNodeBySelection(treeSections, selectedSelection)
    : null;
  const selectedPreviewContent =
    preview && selectedNode && "path" in selectedNode
      ? (preview.contentByPath[selectedNode.path] ?? null)
      : null;
  const displayContent = preview ? selectedPreviewContent : content;
  const chapterStatusMap = useMemo(
    () => new Map((context?.latest_run?.chapter_progress ?? []).map((item) => [item.chapter_id, item.status])),
    [context?.latest_run?.chapter_progress],
  );
  const loadingArtifacts = isPreview || !effectiveCourseId ? false : isArtifactTreeLoading(context?.latest_run?.status);
  const exportUrl = effectiveCourseId
    ? buildExportUrl(effectiveCourseId, {
        completedChaptersOnly: exportCompletedOnly,
        finalOutputsOnly: exportFinalOnly,
        cacheBust: `${snapshot?.current_course_runs.length ?? 0}-${reviewSummary?.report_count ?? 0}`,
      })
    : null;
  const nextContext = {
    draftId: routeContext.draftId,
    courseId: effectiveCourseId,
    runId,
  };

  return (
    <div className="min-h-screen bg-[var(--stitch-background)] text-[var(--stitch-on-surface)]">
      <StitchV4TopNav active="results" context={nextContext} />
      <main className="flex h-[calc(100vh-64px)] overflow-hidden">
        <aside className="flex h-full w-80 flex-col bg-[var(--stitch-surface-container-low)]">
          <div className="p-6">
            <h3 className="font-stitch-headline text-sm font-bold uppercase tracking-[0.24em] text-[var(--stitch-on-surface-variant)]">
              {messages.results.treeTitle}
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {treeSections.map((section) => {
              const openSection = expandedKeys.has(section.key);
              return (
                <div key={section.key} className="mb-4">
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-2 py-1.5 text-left text-sm font-medium"
                    onClick={() =>
                      setExpandedKeys((current) => {
                            const next = new Set(current);
                            if (next.has(section.key)) {
                              next.delete(section.key);
                            } else {
                              next.add(section.key);
                            }
                            return next;
                          })
                    }
                  >
                    <StitchV4MaterialSymbol name={openSection ? "keyboard_arrow_down" : "keyboard_arrow_right"} className="text-sm text-[var(--stitch-on-surface-variant)]" />
                    <span>{section.label}</span>
                  </button>
                  {openSection ? (
                    <div className="ml-4 mt-1 space-y-1">
                      {section.children.map((node) => (
                        <ResultsTreeNodeView
                          key={node.key}
                          node={node}
                          statusLabel={messages.results.statusLabel}
                          selectedSelection={selectedSelection}
                          expandedKeys={expandedKeys}
                          chapterStatusMap={chapterStatusMap}
                          onToggle={(key) =>
                            setExpandedKeys((current) => {
                                  const next = new Set(current);
                                  if (next.has(key)) {
                                    next.delete(key);
                                  } else {
                                    next.add(key);
                                  }
                                  return next;
                                })
                          }
                          onSelect={(selection) => {
                            setSelectedSelection(selection);
                            setExpandedKeys((current) => {
                              const next = new Set(current);
                              for (const key of getResultsTreeSelectionAncestors(selection)) {
                                next.add(key);
                              }
                              return next;
                            });
                          }}
                        />
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
          <div className="bg-[var(--stitch-surface-container-high)] p-4">
            <div className="flex items-center gap-3 rounded-xl bg-[var(--stitch-surface-container-lowest)] p-3 shadow-sm">
              <div className={`h-2 w-2 rounded-full ${loadingArtifacts ? "animate-pulse bg-[var(--stitch-primary)]" : "bg-emerald-500"}`} />
              <div className="flex-1">
                <p className="text-[10px] font-bold uppercase tracking-tight text-[var(--stitch-on-surface-variant)]">
                  {messages.results.systemHealth}
                </p>
                <p className="text-xs font-medium">
                  {loadingArtifacts ? messages.results.snapshotRefreshing : messages.results.snapshotReady}
                </p>
              </div>
            </div>
          </div>
        </aside>

        <section className="relative flex-1 overflow-y-auto bg-[var(--stitch-surface-container-lowest)] p-8 lg:p-12">
          <div className="mx-auto max-w-2xl">
            <div className="mb-10">
              <span className="mb-4 inline-block rounded bg-[var(--stitch-secondary-fixed)] px-2 py-1 text-[10px] font-bold">
                {messages.results.previewBadge}
              </span>
              <h1 className="font-stitch-headline mb-4 text-5xl font-extrabold leading-none tracking-[-0.08em]">
                {selectedNode && "path" in selectedNode
                  ? selectedNode.label
                  : messages.results.title}
              </h1>
              <p className="my-8 bg-[var(--stitch-surface-container-low)] px-6 py-5 text-lg italic text-[var(--stitch-on-surface-variant)]">
                {runId ? messages.results.scopedRun(runId) : messages.results.emptyWorkbench}
              </p>
            </div>
            <article className="space-y-6 leading-relaxed">
              <pre className="whitespace-pre-wrap font-stitch-body text-sm text-[var(--stitch-on-surface)]">
                {displayContent?.content ?? messages.results.noSelection}
              </pre>
            </article>
          </div>
        </section>

        <StitchV4RightRail title={messages.common.context} subtitle={runId ? messages.results.scopedLabel(runId) : messages.results.courseWideState}>
          <div className="space-y-4">
            <section className="rounded-xl bg-[#474746] p-6">
              <h4 className="mb-4 text-xs font-bold uppercase tracking-widest text-white/80">
                {messages.results.summaryTitle}
              </h4>
              <div className="space-y-3 text-sm text-[#f4f1e7]">
                <div className="flex justify-between">
                  <span>{messages.results.reports}</span>
                  <span>{reviewSummary?.report_count ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>{messages.results.issues}</span>
                  <span>{reviewSummary?.issue_count ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>{messages.results.latestRun}</span>
                  <span>{context?.latest_run?.status ? messages.results.statusLabel(context.latest_run.status) : messages.context.none}</span>
                </div>
              </div>
            </section>

            <section className="rounded-xl bg-[#474746] p-6">
              <h4 className="mb-4 text-xs font-bold uppercase tracking-widest text-white/80">
                {messages.results.exportTitle}
              </h4>
              <label className="mb-3 flex items-center gap-3 text-sm text-[#dddad0]">
                <input
                  type="checkbox"
                  checked={exportCompletedOnly}
                  onChange={(event) => setExportCompletedOnly(event.target.checked)}
                />
                {messages.results.exportCompleted}
              </label>
              <label className="flex items-center gap-3 text-sm text-[#dddad0]">
                <input
                  type="checkbox"
                  checked={exportFinalOnly}
                  onChange={(event) => setExportFinalOnly(event.target.checked)}
                />
                {messages.results.exportFinal}
              </label>
            </section>

                <StitchV4ContextRail
                  draftId={routeContext.draftId}
                  courseId={effectiveCourseId}
                  runId={runId}
                />

            <div className="space-y-3 pb-10">
              {exportUrl ? (
                <a
                  href={isPreview ? undefined : exportUrl}
                  className={`flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[var(--stitch-primary)] to-[var(--stitch-primary-container)] px-4 py-4 font-bold text-white shadow-lg shadow-[rgba(0,85,212,0.2)] ${isPreview ? "pointer-events-none opacity-70" : ""}`}
                >
                  <StitchV4MaterialSymbol name="folder_zip" />
                  {messages.results.exportZip}
                </a>
              ) : (
                <div className="rounded-xl bg-[#474746] px-4 py-4 text-center text-sm text-[#dddad0]">
                  {messages.results.exportUnavailable}
                </div>
              )}
            </div>
          </div>
        </StitchV4RightRail>
      </main>
      {error ? (
        <div className="fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-[var(--stitch-error-container)] px-4 py-3 text-sm text-[var(--stitch-on-error-container)]">
          {error}
        </div>
      ) : null}
    </div>
  );
}

function ResultsTreeNodeView({
  node,
  statusLabel,
  selectedSelection,
  expandedKeys,
  chapterStatusMap,
  onToggle,
  onSelect,
}: {
  node: ResultsTreeNode;
  statusLabel: (status: string) => string;
  selectedSelection: string | null;
  expandedKeys: Set<string>;
  chapterStatusMap: Map<string, string>;
  onToggle: (key: string) => void;
  onSelect: (selection: string) => void;
}) {
  if ("path" in node) {
    const selected = selectedSelection === node.key;
    return (
      <button
        type="button"
        className={`flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-sm ${
          selected
            ? "bg-[rgba(29,109,255,0.12)] font-semibold text-[var(--stitch-primary)]"
            : "text-[var(--stitch-on-surface-variant)] hover:bg-[var(--stitch-surface-container-high)]"
        }`}
        onClick={() => onSelect(node.key)}
      >
        <StitchV4MaterialSymbol name="description" className="text-sm" />
        <span>{node.label}</span>
      </button>
    );
  }

  const open = expandedKeys.has(node.key);
  const chapterStatus = chapterStatusMap.get(node.label);
  return (
    <div>
      <button
        type="button"
        className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-[var(--stitch-surface-container-high)]"
        onClick={() => onToggle(node.key)}
      >
        <StitchV4MaterialSymbol
          name={open ? "keyboard_arrow_down" : "keyboard_arrow_right"}
          className="text-sm text-[var(--stitch-on-surface-variant)]"
        />
        <StitchV4MaterialSymbol
          name="folder"
          className={`text-sm ${chapterStatus === "completed" ? "text-[var(--stitch-primary)]" : "text-[var(--stitch-on-surface-variant)]"}`}
        />
        <span>{node.label}</span>
        {chapterStatus ? (
          <span className="ml-auto rounded-full bg-[var(--stitch-surface-container)] px-2 py-0.5 text-[10px] font-bold uppercase text-[var(--stitch-on-surface-variant)]">
            {statusLabel(chapterStatus)}
          </span>
        ) : null}
      </button>
      {open ? (
        <div className="ml-5 mt-1 space-y-1">
          {node.children.map((child) => (
            <ResultsTreeNodeView
              key={child.key}
              node={child}
              statusLabel={statusLabel}
              selectedSelection={selectedSelection}
              expandedKeys={expandedKeys}
              chapterStatusMap={chapterStatusMap}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
