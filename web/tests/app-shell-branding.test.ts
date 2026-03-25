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
const logoSource = readFileSync(
  new URL("../public/countercurrent-logo.svg", import.meta.url),
  "utf8",
);

test("app shell uses the ReCurr brand and renders the header logo", () => {
  assert.match(shellSource, /ReCurr/);
  assert.match(shellSource, /countercurrent-logo\.svg/);
  assert.match(shellSource, /width=\{100\}/);
  assert.match(shellSource, /height=\{100\}/);
  assert.doesNotMatch(shellSource, /Countercurrent/);
  assert.doesNotMatch(shellSource, /Databaseleaning/);
});

test("layout metadata uses the renamed repository brand", () => {
  assert.match(layoutSource, /title:\s*"ReCurr"/);
  assert.match(layoutSource, /description:\s*"Web product shell for the ReCurr blueprint-first pipeline\."/);
});

test("logo uses solid blue wave shapes instead of blue stroke outlines", () => {
  assert.match(logoSource, /fill="#1E6BFF"/);
  assert.doesNotMatch(logoSource, /stroke="#1E6BFF"/);
});
