import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const shellSource = readFileSync(
  new URL("../components/app-shell.tsx", import.meta.url),
  "utf8",
);
const layoutSource = readFileSync(
  new URL("../app/layout.tsx", import.meta.url),
  "utf8",
);

test("app shell uses the Countercurrent brand and renders the header logo", () => {
  assert.match(shellSource, /Countercurrent/);
  assert.match(shellSource, /countercurrent-logo\.svg/);
  assert.doesNotMatch(shellSource, /Databaseleaning/);
});

test("layout metadata uses the renamed repository brand", () => {
  assert.match(layoutSource, /title:\s*"Countercurrent"/);
  assert.match(layoutSource, /description:\s*"Web product shell for the Countercurrent blueprint-first pipeline\."/);
});
