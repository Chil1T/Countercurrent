import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const overviewSource = readFileSync(
  new URL("../components/overview/overview-workbench-v2.tsx", import.meta.url),
  "utf8",
);
const overviewSectionsPath = new URL(
  "../components/overview/overview-v2-sections.tsx",
  import.meta.url,
);
const shellHeaderSource = readFileSync(
  new URL("../components/stitch-v2/shell-header.tsx", import.meta.url),
  "utf8",
);
const shellSidebarSource = readFileSync(
  new URL("../components/stitch-v2/shell-sidebar.tsx", import.meta.url),
  "utf8",
);
const runsRootSource = readFileSync(new URL("../app/runs/page.tsx", import.meta.url), "utf8");
const resultsRootSource = readFileSync(
  new URL("../app/courses/results/page.tsx", import.meta.url),
  "utf8",
);

test("overview v2 workbench exists as a dedicated component with stitched narrative sections", () => {
  assert.match(overviewSource, /export function OverviewWorkbenchV2/);
  assert.match(overviewSource, /OverviewV2Sections/);
  assert.match(overviewSource, /Course Production Workbench/);
  assert.equal(existsSync(overviewSectionsPath), true);
});

test("overview sections carry the higher-fidelity live status and real entry language", () => {
  const overviewSectionsSource = readFileSync(overviewSectionsPath, "utf8");

  assert.match(overviewSectionsSource, /Live Status/);
  assert.match(overviewSectionsSource, /Guided Entry/);
  assert.match(overviewSectionsSource, /本地字幕/);
  assert.match(overviewSectionsSource, /AI 服务配置/);
  assert.match(overviewSectionsSource, /shellState\.navItems\.map/);
});

test("shell extra actions are explicitly marked as coming soon instead of pretending to be real features", () => {
  assert.match(shellHeaderSource, /即将到来/);
  assert.match(shellSidebarSource, /即将到来/);
  assert.match(shellHeaderSource, /disabled/);
  assert.match(shellSidebarSource, /disabled/);
});

test("run root now renders the workbench directly instead of a product empty state", () => {
  assert.match(runsRootSource, /RunSessionWorkbenchV2/);
  assert.doesNotMatch(runsRootSource, /RunEmptyStateV2/);
  assert.equal(
    existsSync(new URL("../components/empty/run-empty-state-v2.tsx", import.meta.url)),
    false,
  );
});

test("results root now renders the snapshot workbench directly instead of a product empty state", () => {
  assert.match(resultsRootSource, /ResultsWorkbenchV2/);
  assert.doesNotMatch(resultsRootSource, /ResultsEmptyStateV2/);
  assert.equal(
    existsSync(new URL("../components/empty/results-empty-state-v2.tsx", import.meta.url)),
    false,
  );
});
