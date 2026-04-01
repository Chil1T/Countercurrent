import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workbenchSource = readFileSync(
  new URL("../components/input/course-draft-workbench-v2.tsx", import.meta.url),
  "utf8",
);
const sectionsSource = readFileSync(
  new URL("../components/input/input-v2-sections.tsx", import.meta.url),
  "utf8",
);

test("input v2 workbench exists as a dedicated component and composes input v2 sections", () => {
  assert.match(workbenchSource, /export function CourseDraftWorkbenchV2/);
  assert.match(workbenchSource, /InputV2Sections/);
  assert.match(workbenchSource, /createCourseDraft/);
  assert.match(workbenchSource, /getCourseDraft/);
});

test("input v2 workbench preserves local subtitle upload and manual transcript authoring semantics", () => {
  assert.match(workbenchSource, /subtitleFileInputRef\.current\?\.click\(\)/);
  assert.match(workbenchSource, /append\("subtitle_files", file, file\.name\)/);
  assert.match(workbenchSource, /new Blob\(\[asset\.content\]/);
  assert.match(workbenchSource, /router\.replace\(`\/courses\/new\/input\?draftId=\$\{nextDraft\.id\}`\)/);
  assert.match(workbenchSource, /router\.push\(`\/courses\/new\/config\?draftId=\$\{draft\.id\}`\)/);
});

test("input v2 workbench and sections keep course-link ui absent", () => {
  assert.doesNotMatch(workbenchSource, /course_url/);
  assert.doesNotMatch(workbenchSource, /课程链接/);
  assert.doesNotMatch(sectionsSource, /course_url/);
  assert.doesNotMatch(sectionsSource, /课程链接/);
});

test("input v2 sections provide stitched subtitle, coming-soon, and draft-summary surfaces", () => {
  assert.match(sectionsSource, /export function InputV2Sections/);
  assert.match(sectionsSource, /Subtitle Assets/);
  assert.match(sectionsSource, /Coming Soon/);
  assert.match(sectionsSource, /课程识别摘要/);
  assert.match(sectionsSource, /保存并识别课程信息/);
});
