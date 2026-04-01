"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { getReviewSummary, type ReviewSummary } from "@/lib/api/artifacts";
import { getCourseDraft, type CourseDraft } from "@/lib/api/course-drafts";
import { getRun, type RunSession } from "@/lib/api/runs";
import { buildContextSections } from "@/lib/context-panel";
import { useLocale } from "@/lib/locale";

export function StitchV4ContextRail({
  draftId,
  runId,
  courseId,
  prefix,
  suffix,
}: {
  draftId?: string | null;
  runId?: string | null;
  courseId?: string | null;
  prefix?: ReactNode;
  suffix?: ReactNode;
}) {
  const { locale } = useLocale();
  const [draft, setDraft] = useState<CourseDraft | null>(null);
  const [run, setRun] = useState<RunSession | null>(null);
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const nextDraft = draftId ? await getCourseDraft(draftId).catch(() => null) : null;
      const nextRun = runId ? await getRun(runId).catch(() => null) : null;
      const resolvedCourseId = courseId ?? nextRun?.course_id ?? nextDraft?.course_id ?? null;
      const nextReview = resolvedCourseId
        ? await getReviewSummary(resolvedCourseId).catch(() => null)
        : null;

      if (cancelled) {
        return;
      }

      setDraft(nextDraft);
      setRun(nextRun);
      setReviewSummary(nextReview);
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [courseId, draftId, runId]);

  const sections = useMemo(
    () => buildContextSections({ locale, draft, run, reviewSummary }),
    [draft, locale, reviewSummary, run],
  );

  return (
    <div className="space-y-4">
      {prefix}
      {sections.map((section) => (
        <section key={section.title} className="rounded-xl bg-[#474746] p-5">
          <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-[#dddad0]/70">
            {section.title}
          </h3>
          <ul className="space-y-2 text-sm text-[#f4f1e7]">
            {section.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}
      {suffix}
    </div>
  );
}
