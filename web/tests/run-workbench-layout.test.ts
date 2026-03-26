import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workbenchSource = readFileSync(
  new URL("../components/run/run-session-workbench.tsx", import.meta.url),
  "utf8",
);

test("run workbench removes the duplicate stage rail and lets runtime flow use the main content column", () => {
  assert.doesNotMatch(workbenchSource, /<h3 className="text-xl font-semibold">阶段轨道<\/h3>/);
  assert.doesNotMatch(workbenchSource, /xl:grid-cols-\[minmax\(0,1\.1fr\)_minmax\(320px,0\.9fr\)\]/);
  assert.match(workbenchSource, /xl:grid-cols-\[minmax\(0,1\.3fr\)_minmax\(320px,0\.9fr\)\]/);
  assert.match(workbenchSource, /<h3 className="text-lg font-semibold">数据通路<\/h3>/);
  assert.match(workbenchSource, /<h3 className="text-lg font-semibold">错误与日志<\/h3>/);
});
