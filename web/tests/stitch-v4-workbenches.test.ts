import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const overviewSource = readFileSync(
  new URL("../components/stitch-v4/overview-page.tsx", import.meta.url),
  "utf8",
);
const inputSource = readFileSync(
  new URL("../components/stitch-v4/input-page.tsx", import.meta.url),
  "utf8",
);
const configSource = readFileSync(
  new URL("../components/stitch-v4/config-page.tsx", import.meta.url),
  "utf8",
);
const runSource = readFileSync(
  new URL("../components/stitch-v4/run-page.tsx", import.meta.url),
  "utf8",
);
const resultsSource = readFileSync(
  new URL("../components/stitch-v4/results-page.tsx", import.meta.url),
  "utf8",
);
const localeSource = readFileSync(new URL("../lib/locale.tsx", import.meta.url), "utf8");

test("stitch v4 overview page preserves real product routing rather than static placeholder anchors", () => {
  assert.match(overviewSource, /buildProductHref\("input", context\)/);
  assert.match(overviewSource, /buildProductHref\("config", context\)/);
  assert.match(overviewSource, /buildProductHref\("run", context\)/);
  assert.match(overviewSource, /buildProductHref\("results", context\)/);
  assert.match(overviewSource, /useLocale/);
});

test("stitch v4 input page keeps local asset creation wired to course draft apis", () => {
  assert.match(inputSource, /createCourseDraft/);
  assert.match(inputSource, /getCourseDraft/);
  assert.match(inputSource, /subtitle_assets|subtitle_files/);
  assert.match(inputSource, /messages\.input\.slotLabels/);
  assert.doesNotMatch(inputSource, /course_url/);
  assert.doesNotMatch(inputSource, /课程链接/);
});

test("stitch v4 config page keeps template save, ai service config, and run creation wiring", () => {
  assert.match(configSource, /listTemplates/);
  assert.match(configSource, /getGuiRuntimeConfig/);
  assert.match(configSource, /saveGuiRuntimeConfig/);
  assert.match(configSource, /saveCourseDraftConfig/);
  assert.match(configSource, /createRun/);
  assert.match(configSource, /grid-cols-\[minmax\(0,1\.5fr\)_minmax\(320px,0\.9fr\)\]/);
  assert.match(configSource, /lg:grid/);
  assert.match(configSource, /<aside className="mt-10 rounded-2xl bg-\[var\(--stitch-surface-container-lowest\)\]/);
  assert.match(configSource, /max-w-2xl font-medium text-\[var\(--stitch-on-surface-variant\)\]/);
  assert.doesNotMatch(configSource, /课程级运行覆盖/);
  assert.doesNotMatch(configSource, /Course Provider Override/);
});

test("stitch v4 run page keeps real run status, log, resume, clean, and unstarted semantics", () => {
  assert.match(runSource, /getRun/);
  assert.match(runSource, /getRunLog/);
  assert.match(runSource, /subscribeRunEvents/);
  assert.match(runSource, /subscribeRunLogEvents/);
  assert.match(runSource, /resumeRun/);
  assert.match(runSource, /cleanRun/);
  assert.match(runSource, /useLocale/);
});

test("stitch v4 user-facing copy removes internal implementation wording", () => {
  assert.doesNotMatch(localeSource, /不再退回伪空态/);
  assert.doesNotMatch(localeSource, /不会伪造任何进度或日志/);
  assert.doesNotMatch(localeSource, /即使任务尚未开始/);
  assert.doesNotMatch(localeSource, /The task has not started\\. The workbench is ready/);
  assert.doesNotMatch(localeSource, /fake empty states/);
  assert.match(localeSource, /当前还没有运行记录。请先从配置页启动任务。/);
  assert.match(localeSource, /There is no run record yet\./);
});

test("stitch v4 results page keeps snapshot tree, preview, review summary, and export filters", () => {
  assert.match(resultsSource, /getResultsSnapshot/);
  assert.match(resultsSource, /getResultsSnapshotContent/);
  assert.match(resultsSource, /getCourseResultsContext/);
  assert.match(resultsSource, /getReviewSummary/);
  assert.match(resultsSource, /buildExportUrl/);
  assert.match(resultsSource, /buildResultsSnapshotTree/);
  assert.match(resultsSource, /historical-courses/);
  assert.match(resultsSource, /current-course/);
  assert.doesNotMatch(resultsSource, /intermediate/);
  assert.doesNotMatch(resultsSource, /runtime\/runtime_state\.json/);
});
