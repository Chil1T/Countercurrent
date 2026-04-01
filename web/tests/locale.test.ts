import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const localeSource = readFileSync(new URL("../lib/locale.tsx", import.meta.url), "utf8");

test("locale provider defaults to zh-CN and persists the chosen locale", () => {
  assert.match(localeSource, /"zh-CN"/);
  assert.match(localeSource, /recurr\.locale/);
  assert.match(localeSource, /toggleLocale/);
  assert.match(localeSource, /document\.documentElement\.lang/);
});
