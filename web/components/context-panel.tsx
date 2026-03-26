"use client";

import { useEffect, useMemo, useState } from "react";

import { getReviewSummary, type ReviewSummary } from "@/lib/api/artifacts";
import { getCourseDraft, type CourseDraft } from "@/lib/api/course-drafts";
import { getRun, type RunSession } from "@/lib/api/runs";
import { buildContextSections } from "@/lib/context-panel";

export function ContextPanel({
  draftId,
  runId,
  courseId,
}: {
  draftId?: string | null;
  runId?: string | null;
  courseId?: string | null;
}) {
  const [draft, setDraft] = useState<CourseDraft | null>(null);
  const [run, setRun] = useState<RunSession | null>(null);
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadContext() {
      const nextDraft = draftId
        ? await getCourseDraft(draftId).catch(() => null)
        : null;
      const nextRun = runId ? await getRun(runId).catch(() => null) : null;
      const resolvedCourseId = courseId ?? nextRun?.course_id ?? nextDraft?.course_id ?? null;
      const nextReviewSummary = resolvedCourseId
        ? await getReviewSummary(resolvedCourseId).catch(() => null)
        : null;

      if (cancelled) {
        return;
      }

      setDraft(nextDraft);
      setRun(nextRun);
      setReviewSummary(nextReviewSummary);
    }

    void loadContext();

    return () => {
      cancelled = true;
    };
  }, [courseId, draftId, runId]);

  const sections = useMemo(
    () =>
      buildContextSections({
        draft,
        run,
        reviewSummary,
      }),
    [draft, reviewSummary, run],
  );

  return (
    <div className="rounded-[22px] bg-white/8 p-4">
      <div className="text-xs uppercase tracking-[0.24em] text-stone-400">Context</div>
      <div className="mt-3 grid gap-4 text-sm text-stone-300 md:grid-cols-3 lg:grid-cols-2 xl:grid-cols-1">
        {sections.map((section) => (
          <div key={section.title}>
            <div className="font-medium text-stone-100">{section.title}</div>
            <ul className="mt-1 space-y-1.5 leading-6">
              {section.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
