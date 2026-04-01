import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workbenchSource = readFileSync(
  new URL("../components/config/template-config-workbench-v2.tsx", import.meta.url),
  "utf8",
);
const sectionsSource = readFileSync(
  new URL("../components/config/config-v2-sections.tsx", import.meta.url),
  "utf8",
);

test("config v2 workbench exists as a dedicated component and composes config v2 sections", () => {
  assert.match(workbenchSource, /export function TemplateConfigWorkbenchV2/);
  assert.match(workbenchSource, /ConfigV2Sections/);
  assert.match(workbenchSource, /listTemplates/);
  assert.match(workbenchSource, /getGuiRuntimeConfig/);
  assert.match(workbenchSource, /saveCourseDraftConfig/);
  assert.match(workbenchSource, /saveGuiRuntimeConfig/);
  assert.match(workbenchSource, /createRun/);
});

test("config v2 workbench preserves runtime and run action semantics", () => {
  assert.match(workbenchSource, /router\.push\(\s*`\/runs\/\$\{run\.id\}/);
  assert.match(workbenchSource, /run_kind:\s*"chapter"/);
  assert.match(workbenchSource, /run_kind:\s*"global"/);
  assert.match(workbenchSource, /runReviewOverride/);
});

test("config v2 sections keep AI service configuration collapsed and runtime override controls hidden", () => {
  assert.match(sectionsSource, /AI 服务配置/);
  assert.match(sectionsSource, /runtimeDefaultsDefaultOpen/);
  assert.doesNotMatch(sectionsSource, /课程级运行覆盖/);
  assert.doesNotMatch(sectionsSource, /provider 覆盖/);
  assert.doesNotMatch(sectionsSource, /Base URL 覆盖/);
});

test("config v2 sections keep template controls and run controls visible", () => {
  assert.match(sectionsSource, /Logic Parameters/);
  assert.match(sectionsSource, /启动 \/ 继续运行/);
  assert.match(sectionsSource, /更新全局汇总/);
  assert.match(sectionsSource, /Templates/);
});
