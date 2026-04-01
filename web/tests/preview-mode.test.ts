import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const runPageSource = readFileSync(
  new URL("../app/runs/[runId]/page.tsx", import.meta.url),
  "utf8",
);
const resultsPageSource = readFileSync(
  new URL("../app/courses/[courseId]/results/page.tsx", import.meta.url),
  "utf8",
);
const runWorkbenchSource = readFileSync(
  new URL("../components/run/run-session-workbench.tsx", import.meta.url),
  "utf8",
);
const resultsWorkbenchSource = readFileSync(
  new URL("../components/results/results-workbench.tsx", import.meta.url),
  "utf8",
);

test("run page supports query-driven preview mode and passes preview data into the workbench", () => {
  assert.match(runPageSource, /mode\?: string/);
  assert.match(runPageSource, /scenario\?: string/);
  assert.match(runPageSource, /resolvedSearchParams\.mode === "preview"/);
  assert.match(runPageSource, /<RunSessionWorkbench[\s\S]*preview=\{preview\}[\s\S]*\/>/);
});

test("results page supports query-driven preview mode and passes preview data into the workbench", () => {
  assert.match(resultsPageSource, /mode\?: string/);
  assert.match(resultsPageSource, /scenario\?: string/);
  assert.match(resultsPageSource, /resolvedSearchParams\.mode === "preview"/);
  assert.match(
    resultsPageSource,
    /<ResultsWorkbench[\s\S]*courseId=\{courseId\}[\s\S]*runId=\{resolvedSearchParams\.runId \?\? null\}[\s\S]*preview=\{preview\}[\s\S]*\/>/,
  );
});

test("preview routes use empty-shell navigation instead of leaking preview ids into product flow", () => {
  assert.match(runPageSource, /buildAppShellState\(preview \? "\/runs" : `\/runs\/\$\{runId\}`/);
  assert.match(resultsPageSource, /buildAppShellState\(preview \? "\/courses\/results" : `\/courses\/\$\{courseId\}\/results`/);
});

test("run workbench renders a preview badge and disables real actions in preview mode", () => {
  assert.match(runWorkbenchSource, /Preview/);
  assert.match(runWorkbenchSource, /preview\?:/);
  assert.match(runWorkbenchSource, /disabled=\{isPreview \|\| !canResume \|\| actionState !== "idle"\}/);
  assert.match(runWorkbenchSource, /disabled=\{isPreview \|\| !canClean\}/);
});

test("results workbench renders a preview badge and disables real export in preview mode", () => {
  assert.match(resultsWorkbenchSource, /Preview/);
  assert.match(resultsWorkbenchSource, /preview\?:/);
  assert.match(resultsWorkbenchSource, /if \(preview\)/);
  assert.match(resultsWorkbenchSource, /Preview only/);
});
