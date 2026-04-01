import { StitchV4ConfigPage } from "@/components/stitch-v4/config-page";

export default async function ConfigPage({
  searchParams,
}: {
  searchParams: Promise<{ draftId?: string; runId?: string; courseId?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  return (
    <StitchV4ConfigPage
      initialDraftId={resolvedSearchParams.draftId ?? null}
      context={{
        draftId: resolvedSearchParams.draftId ?? null,
        runId: resolvedSearchParams.runId ?? null,
        courseId: resolvedSearchParams.courseId ?? null,
      }}
    />
  );
}
