import { StitchV4RunPage } from "@/components/stitch-v4/run-page";

export default async function RunsPage({
  searchParams,
}: {
  searchParams: Promise<{ draftId?: string; courseId?: string; runId?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  return (
    <StitchV4RunPage
      context={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: resolvedSearchParams.runId ?? null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
      initialState={{
        draft_id: resolvedSearchParams.draftId ?? null,
        course_id: resolvedSearchParams.courseId ?? null,
      }}
    />
  );
}
