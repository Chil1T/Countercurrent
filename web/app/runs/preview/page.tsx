import { StitchV4RunPage } from "@/components/stitch-v4/run-page";
import {
  buildRunWorkbenchPreview,
  resolvePreviewScenario,
} from "@/lib/preview/workbench";

export default async function RunPreviewPage({
  searchParams,
}: {
  searchParams: Promise<{ mode?: string; scenario?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  const preview =
    resolvedSearchParams.mode === "preview"
      ? buildRunWorkbenchPreview(resolvePreviewScenario(resolvedSearchParams.scenario, "running"))
      : buildRunWorkbenchPreview("running");

  return <StitchV4RunPage context={{}} preview={preview} />;
}
