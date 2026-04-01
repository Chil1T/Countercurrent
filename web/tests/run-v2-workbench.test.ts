import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workbenchSource = readFileSync(
  new URL("../components/run/run-session-workbench-v2.tsx", import.meta.url),
  "utf8",
);
const sectionsSource = readFileSync(
  new URL("../components/run/run-v2-sections.tsx", import.meta.url),
  "utf8",
);

test("run v2 workbench exists as a dedicated component and composes run v2 sections", () => {
  assert.match(workbenchSource, /export function RunSessionWorkbenchV2/);
  assert.match(workbenchSource, /RunV2Sections/);
  assert.match(workbenchSource, /getRun/);
  assert.match(workbenchSource, /getRunLog/);
  assert.match(workbenchSource, /subscribeRunEvents/);
  assert.match(workbenchSource, /subscribeRunLogEvents/);
});

test("run v2 workbench preserves runtime actions and preview boundary", () => {
  assert.match(workbenchSource, /resumeRun/);
  assert.match(workbenchSource, /cleanRun/);
  assert.match(workbenchSource, /previewResultsHref/);
  assert.match(workbenchSource, /isPreview/);
  assert.match(workbenchSource, /actionState/);
});

test("run v2 sections keep run summary, chapter board, runtime flow, and log panels", () => {
  assert.match(sectionsSource, /export function RunV2Sections/);
  assert.match(sectionsSource, /Run Mission Control/);
  assert.match(sectionsSource, /章节执行/);
  assert.match(sectionsSource, /数据通路/);
  assert.match(sectionsSource, /错误与日志/);
  assert.match(sectionsSource, /Preview only/);
});
