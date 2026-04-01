import { StitchV4ResultsPage } from "@/components/stitch-v4/results-page";

export default async function ResultsPage({
  searchParams,
}: {
  searchParams: Promise<{ draftId?: string; courseId?: string; runId?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  return (
    <StitchV4ResultsPage
      courseId={resolvedSearchParams.courseId ?? null}
      runId={resolvedSearchParams.runId ?? null}
      context={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: resolvedSearchParams.runId ?? null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    />
  );
}
