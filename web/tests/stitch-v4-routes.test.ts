import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const homeSource = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
const inputPageSource = readFileSync(
  new URL("../app/courses/new/input/page.tsx", import.meta.url),
  "utf8",
);
const configPageSource = readFileSync(
  new URL("../app/courses/new/config/page.tsx", import.meta.url),
  "utf8",
);
const runsPageSource = readFileSync(new URL("../app/runs/page.tsx", import.meta.url), "utf8");
const runPageSource = readFileSync(
  new URL("../app/runs/[runId]/page.tsx", import.meta.url),
  "utf8",
);
const resultsRootSource = readFileSync(
  new URL("../app/courses/results/page.tsx", import.meta.url),
  "utf8",
);
const resultsPageSource = readFileSync(
  new URL("../app/courses/[courseId]/results/page.tsx", import.meta.url),
  "utf8",
);
const chromeSource = readFileSync(
  new URL("../components/stitch-v4/chrome.tsx", import.meta.url),
  "utf8",
);
const layoutSource = readFileSync(new URL("../app/layout.tsx", import.meta.url), "utf8");
const globalsSource = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");
const logoAsset = readFileSync(new URL("../public/brand/recurr-logo.svg", import.meta.url), "utf8");
const iconFontAsset = readFileSync(
  new URL("../public/fonts/material-symbols-outlined.ttf", import.meta.url),
);

test("default product routes switch to stitch v4 page components instead of legacy v2 workbenches", () => {
  assert.match(homeSource, /StitchV4OverviewPage/);
  assert.match(inputPageSource, /StitchV4InputPage/);
  assert.match(configPageSource, /StitchV4ConfigPage/);
  assert.match(runsPageSource, /StitchV4RunPage/);
  assert.match(runPageSource, /StitchV4RunPage/);
  assert.match(resultsRootSource, /StitchV4ResultsPage/);
  assert.match(resultsPageSource, /StitchV4ResultsPage/);

  assert.doesNotMatch(homeSource, /OverviewWorkbenchV2/);
  assert.doesNotMatch(inputPageSource, /CourseDraftWorkbenchV2/);
  assert.doesNotMatch(configPageSource, /TemplateConfigWorkbenchV2/);
  assert.doesNotMatch(runsPageSource, /RunSessionWorkbenchV2/);
  assert.doesNotMatch(resultsRootSource, /ResultsWorkbenchV2/);
});

test("run and results routes continue to render real product workbenches instead of empty-state pages", () => {
  assert.doesNotMatch(runsPageSource, /RunEmptyStateV2/);
  assert.doesNotMatch(resultsRootSource, /ResultsEmptyStateV2/);
  assert.doesNotMatch(runPageSource, /mode === "preview"/);
  assert.doesNotMatch(resultsPageSource, /mode === "preview"/);
});

test("stitch v4 chrome uses the ReCurr brand anchor instead of the old product name", () => {
  assert.match(chromeSource, /messages\.brand\.title/);
  assert.match(chromeSource, /\/brand\/recurr-logo\.svg/);
  assert.doesNotMatch(
    chromeSource,
    /<div className="flex h-12 w-12 items-center justify-center rounded-full bg-\[var\(--stitch-surface-container-lowest\)\]/,
  );
  assert.doesNotMatch(chromeSource, /Atelier Course Production/);
  assert.match(chromeSource, /toggleLocale/);
});

test("root layout installs the locale provider for runtime language switching", () => {
  assert.match(layoutSource, /LocaleProvider/);
});

test("stitch v4 brand logo is provided as a static svg asset", () => {
  assert.match(logoAsset, /<svg/);
  assert.match(logoAsset, /fill="#1E6BFF"/);
  assert.match(logoAsset, /viewBox="85 180 490 280"/);
});

test("material symbols font import uses the supported axes format", () => {
  assert.match(globalsSource, /@font-face/);
  assert.match(globalsSource, /\/fonts\/material-symbols-outlined\.ttf/);
  assert.doesNotMatch(globalsSource, /fonts\.googleapis\.com/);
});

test("material symbols font is vendored locally for offline icon rendering", () => {
  assert.ok(iconFontAsset.byteLength > 0);
});
