import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const runPreviewSource = readFileSync(
  new URL("../app/runs/preview/page.tsx", import.meta.url),
  "utf8",
);
const resultsPreviewSource = readFileSync(
  new URL("../app/courses/preview/results/page.tsx", import.meta.url),
  "utf8",
);

test("dedicated preview routes use stitch v4 pages instead of product dynamic routes", () => {
  assert.match(runPreviewSource, /StitchV4RunPage/);
  assert.match(resultsPreviewSource, /StitchV4ResultsPage/);
  assert.match(runPreviewSource, /buildRunWorkbenchPreview/);
  assert.match(resultsPreviewSource, /buildResultsWorkbenchPreview/);
});

test("preview routes still require explicit preview mode semantics", () => {
  assert.match(runPreviewSource, /mode === "preview"/);
  assert.match(resultsPreviewSource, /mode === "preview"/);
  assert.doesNotMatch(runPreviewSource, /RunSessionWorkbenchV2/);
  assert.doesNotMatch(resultsPreviewSource, /ResultsWorkbenchV2/);
});
