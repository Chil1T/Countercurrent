import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workbenchSource = readFileSync(
  new URL("../components/results/results-workbench-v2.tsx", import.meta.url),
  "utf8",
);
const sectionsSource = readFileSync(
  new URL("../components/results/results-v2-sections.tsx", import.meta.url),
  "utf8",
);

test("results v2 workbench exists as a dedicated component and composes results v2 sections", () => {
  assert.match(workbenchSource, /export function ResultsWorkbenchV2/);
  assert.match(workbenchSource, /ResultsV2Sections/);
  assert.match(workbenchSource, /getArtifactTree/);
  assert.match(workbenchSource, /getReviewSummary/);
  assert.match(workbenchSource, /getCourseResultsContext/);
  assert.match(workbenchSource, /subscribeRunEvents/);
});

test("results v2 workbench preserves course latest-run semantics and stable tree selection helpers", () => {
  assert.match(workbenchSource, /context\?\.latest_run\?\.chapter_progress \?\? \[\]/);
  assert.match(workbenchSource, /isArtifactTreeLoading\(context\?\.latest_run\?\.status\)/);
  assert.match(workbenchSource, /findArtifactTreeNodeByPath/);
  assert.match(workbenchSource, /getArtifactTreePathAncestors/);
  assert.doesNotMatch(workbenchSource, /run\?\.chapter_progress \?\? context\?\.latest_run\?\.chapter_progress/);
});

test("results v2 sections keep the file tree, preview pane, and export controls", () => {
  assert.match(sectionsSource, /export function ResultsV2Sections/);
  assert.match(sectionsSource, /Artifact Tree/);
  assert.match(sectionsSource, /Reviewer \/ Export/);
  assert.match(sectionsSource, /Artifact Preview/);
  assert.match(sectionsSource, /只导出已完成章节/);
  assert.match(sectionsSource, /仅导出最终产物/);
  assert.match(sectionsSource, /Preview only/);
});
