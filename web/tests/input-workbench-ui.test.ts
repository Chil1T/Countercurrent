import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(
  new URL("../components/input/course-draft-workbench.tsx", import.meta.url),
  "utf8",
);

test("input workbench no longer renders a course url field", () => {
  assert.doesNotMatch(source, /课程链接/);
  assert.doesNotMatch(source, /courseUrl/);
});

test("input workbench does not append course_url when creating a draft", () => {
  assert.doesNotMatch(source, /append\("course_url"/);
  assert.doesNotMatch(source, /course_url:/);
});
