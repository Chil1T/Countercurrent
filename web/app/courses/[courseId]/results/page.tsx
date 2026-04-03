import { StitchV4ResultsPage } from "@/components/stitch-v4/results-page";

export default async function ResultsPage({
  params,
  searchParams,
}: {
  params: Promise<{ courseId: string }>;
  searchParams: Promise<{ draftId?: string; runId?: string }>;
}) {
  const { courseId } = await params;
  const resolvedSearchParams = await searchParams;
  return (
    <StitchV4ResultsPage
      courseId={courseId}
      runId={resolvedSearchParams.runId ?? null}
      context={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: resolvedSearchParams.runId ?? null,
        courseId,
      }}
    />
  );
}
