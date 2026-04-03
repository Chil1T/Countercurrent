import { StitchV4ResultsPage } from "@/components/stitch-v4/results-page";
import {
  buildResultsWorkbenchPreview,
  resolvePreviewScenario,
} from "@/lib/preview/workbench";

export default async function ResultsPreviewPage({
  searchParams,
}: {
  searchParams: Promise<{ mode?: string; scenario?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  const scenario = resolvePreviewScenario(resolvedSearchParams.scenario, "completed");
  const preview =
    resolvedSearchParams.mode === "preview"
      ? buildResultsWorkbenchPreview(scenario)
      : buildResultsWorkbenchPreview("completed");

  return (
    <StitchV4ResultsPage
      courseId={preview.courseId}
      runId={preview.runId}
      preview={preview}
      context={{}}
    />
  );
}
