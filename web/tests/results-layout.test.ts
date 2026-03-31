import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workbenchSource = readFileSync(
  new URL("../components/results/results-workbench.tsx", import.meta.url),
  "utf8",
);
const pageSource = readFileSync(
  new URL("../app/courses/[courseId]/results/page.tsx", import.meta.url),
  "utf8",
);

test("results page keeps the left rail sticky and elastic to viewport height without rigid tree cutoff", () => {
  assert.match(workbenchSource, /xl:sticky xl:top-24 xl:self-start/);
  assert.doesNotMatch(workbenchSource, /h-\[26rem\]/);
  assert.match(workbenchSource, /xl:h-\[calc\(100vh-8\.5rem\)\] xl:grid-rows-\[minmax\(0,1fr\)_auto\]/);
  assert.match(workbenchSource, /flex-1 overflow-x-hidden overflow-y-auto pr-1 text-sm text-stone-700/);
});

test("results page keeps the preview header sticky while the preview body scrolls", () => {
  assert.match(workbenchSource, /文件预览/);
  assert.match(workbenchSource, /xl:sticky xl:top-24 xl:self-start/);
  assert.match(workbenchSource, /overflow-hidden/);
  assert.match(workbenchSource, /sticky top-0 z-10/);
  assert.doesNotMatch(workbenchSource, /xl:-mx-6/);
  assert.doesNotMatch(workbenchSource, /xl:-mt-6/);
});

test("results page wires runId into the workbench and uses course latest run status for loading hints", () => {
  assert.match(
    pageSource,
    /<ResultsWorkbench courseId=\{courseId\} runId=\{resolvedSearchParams\.runId \?\? null\} \/>/,
  );
  assert.match(workbenchSource, /getRun/);
  assert.match(workbenchSource, /文件仍在生成中/);
  assert.match(workbenchSource, /isArtifactTreeLoading\(context\?\.latest_run\?\.status\)/);
});
