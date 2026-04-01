import { StitchV4RunPage } from "@/components/stitch-v4/run-page";

export default async function RunPage({
  params,
  searchParams,
}: {
  params: Promise<{ runId: string }>;
  searchParams: Promise<{ draftId?: string; courseId?: string }>;
}) {
  const { runId } = await params;
  const resolvedSearchParams = await searchParams;
  return (
    <StitchV4RunPage
      runId={runId}
      context={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    />
  );
}
