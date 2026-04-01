import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workbenchSource = readFileSync(
  new URL("../components/results/results-workbench.tsx", import.meta.url),
  "utf8",
);

test("results workbench derives chapter status from the course-level latest run context", () => {
  assert.match(workbenchSource, /const activeChapterProgress = context\?\.latest_run\?\.chapter_progress \?\? \[\];/);
  assert.doesNotMatch(workbenchSource, /run\?\.chapter_progress \?\? context\?\.latest_run\?\.chapter_progress/);
});

test("results workbench uses course-level latest run status for artifact loading hints", () => {
  assert.match(workbenchSource, /const loadingArtifacts = isPreview \? false : isArtifactTreeLoading\(context\?\.latest_run\?\.status\);/);
  assert.doesNotMatch(workbenchSource, /const loadingArtifacts = isArtifactTreeLoading\(run\?\.status\);/);
});

test("results workbench keeps scoped run information as a label only", () => {
  assert.match(workbenchSource, /Scoped view/);
  assert.match(workbenchSource, /Course view/);
});
