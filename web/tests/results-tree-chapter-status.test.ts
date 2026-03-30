import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workbenchSource = readFileSync(
  new URL("../components/results/results-workbench.tsx", import.meta.url),
  "utf8"
);

test("results tree injects course-level chapter status into chapter directory nodes", () => {
  // We expect to see a visual badge or layout displaying the chapter status in the tree.
  // The backend chapter status injection logic should be visible in the component.
  assert.match(workbenchSource, /chapterStatusMap/);
  assert.match(workbenchSource, /bg-emerald-100 text-emerald-700/);
});
