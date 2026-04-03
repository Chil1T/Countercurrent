import { StitchV4InputPage } from "@/components/stitch-v4/input-page";

export default async function InputPage({
  searchParams,
}: {
  searchParams: Promise<{ draftId?: string; runId?: string; courseId?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  return (
    <StitchV4InputPage
      initialDraftId={resolvedSearchParams.draftId ?? null}
      context={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: resolvedSearchParams.runId ?? null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    />
  );
}
