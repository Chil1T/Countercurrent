import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workbenchSource = readFileSync(
  new URL("../components/run/run-session-workbench.tsx", import.meta.url),
  "utf8"
);

test("run workbench renders a dedicated chapter progress area", () => {
  assert.match(workbenchSource, /<h3 className="text-xl font-semibold">章节执行<\/h3>/);
  assert.match(workbenchSource, /chapter\.chapter_id/);
  assert.match(workbenchSource, /chapter\.status/);
  assert.match(workbenchSource, /chapter\.current_step/);
  assert.match(workbenchSource, /chapter\.completed_step_count/);
  assert.match(workbenchSource, /chapter\.total_step_count/);
  assert.match(workbenchSource, /chapter\.export_ready/);
});
