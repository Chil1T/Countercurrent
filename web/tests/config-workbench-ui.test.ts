import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(
  new URL("../components/config/template-config-workbench.tsx", import.meta.url),
  "utf8",
);

test("config workbench renames runtime defaults to AI service configuration", () => {
  assert.match(source, /configWorkbenchCopy\.runtimeDefaultsTitle/);
  assert.doesNotMatch(source, /运行后端默认值/);
});

test("config workbench keeps AI service configuration collapsed by default", () => {
  assert.match(source, /<details[\s\S]*runtimeDefaultsDefaultOpen[\s\S]*<summary[\s\S]*runtimeDefaultsTitle/);
});

test("config workbench hides course-level runtime override controls", () => {
  assert.doesNotMatch(source, /课程级运行覆盖/);
  assert.doesNotMatch(source, /provider 覆盖/);
  assert.doesNotMatch(source, /Base URL 覆盖/);
});
