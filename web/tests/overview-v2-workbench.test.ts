import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const overviewSource = readFileSync(
  new URL("../components/overview/overview-workbench-v2.tsx", import.meta.url),
  "utf8",
);
const runEmptyStateSource = readFileSync(
  new URL("../components/empty/run-empty-state-v2.tsx", import.meta.url),
  "utf8",
);
const resultsEmptyStateSource = readFileSync(
  new URL("../components/empty/results-empty-state-v2.tsx", import.meta.url),
  "utf8",
);

test("overview v2 workbench exists as a dedicated component with stitched narrative sections", () => {
  assert.match(overviewSource, /export function OverviewWorkbenchV2/);
  assert.match(overviewSource, /Workspace Overview/);
  assert.match(overviewSource, /Course Production Workbench/);
  assert.match(overviewSource, /shellState\.navItems\.map/);
  assert.match(overviewSource, /本地字幕与多章节素材输入/);
});

test("run empty state v2 is a product empty state rather than preview copy", () => {
  assert.match(runEmptyStateSource, /export function RunEmptyStateV2/);
  assert.match(runEmptyStateSource, /尚未创建运行/);
  assert.match(runEmptyStateSource, /配置页保存模板配置并启动运行/);
  assert.doesNotMatch(runEmptyStateSource, /mode=preview/);
  assert.doesNotMatch(runEmptyStateSource, /Preview/);
});

test("results empty state v2 is a product empty state rather than preview copy", () => {
  assert.match(resultsEmptyStateSource, /export function ResultsEmptyStateV2/);
  assert.match(resultsEmptyStateSource, /尚无运行结果/);
  assert.match(resultsEmptyStateSource, /请先完成一次课程运行/);
  assert.doesNotMatch(resultsEmptyStateSource, /mode=preview/);
  assert.doesNotMatch(resultsEmptyStateSource, /Preview/);
});
