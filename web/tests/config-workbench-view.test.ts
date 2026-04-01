import test from "node:test";
import assert from "node:assert/strict";

import {
  getConfigWorkbenchCopy,
  getConfigWorkbenchLayout,
} from "../lib/config-workbench-view.ts";

test("config workbench uses the localized review copy", () => {
  const copy = getConfigWorkbenchCopy();

  assert.equal(copy.reviewEnabledLabel, "启用 Review");
  assert.equal(
    copy.reviewEnabledHelpText,
    "开启后，系统会在生成过程中增加 Review 环节，以帮助提升结果质量。默认关闭。",
  );
});

test("config workbench keeps course overrides behind advanced settings by default", () => {
  const copy = getConfigWorkbenchCopy();
  const layout = getConfigWorkbenchLayout();

  assert.equal(copy.runtimeDefaultsTitle, "AI 服务配置");
  assert.equal(layout.runtimeDefaultsDefaultOpen, false);
});

test("config workbench uses a shared two-column field layout for density and review strategy", () => {
  const layout = getConfigWorkbenchLayout();

  assert.equal(layout.primaryFieldGridClass.includes("md:grid-cols-2"), true);
  assert.equal(layout.primaryFieldGridClass.includes("items-stretch"), true);
  assert.equal(layout.primaryFieldCardClass.includes("h-full"), true);
});
