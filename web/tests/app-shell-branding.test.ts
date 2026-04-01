import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const shellSource = readFileSync(
  new URL("../components/app-shell.tsx", import.meta.url),
  "utf8",
);
const shellHeaderSource = readFileSync(
  new URL("../components/stitch-v2/shell-header.tsx", import.meta.url),
  "utf8",
);
const shellSidebarSource = readFileSync(
  new URL("../components/stitch-v2/shell-sidebar.tsx", import.meta.url),
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
const globalsSource = readFileSync(
  new URL("../app/globals.css", import.meta.url),
  "utf8",
);

test("app shell uses the ReCurr brand and renders the header logo", () => {
  assert.match(shellSource, /ShellHeader/);
  assert.match(shellHeaderSource, /ReCurr/);
  assert.match(shellHeaderSource, /countercurrent-logo\.svg/);
  assert.match(shellHeaderSource, /width=\{44\}/);
  assert.match(shellHeaderSource, /height=\{44\}/);
  assert.doesNotMatch(shellSource, /Countercurrent/);
  assert.doesNotMatch(shellSource, /Databaseleaning/);
});

test("layout metadata uses the renamed repository brand", () => {
  assert.match(layoutSource, /title:\s*"ReCurr"/);
  assert.match(layoutSource, /description:\s*"Web product shell for the ReCurr blueprint-first pipeline\."/);
});

test("layout switches the shell typography to Manrope and Inter", () => {
  assert.match(layoutSource, /import\s*\{\s*Inter,\s*Manrope\s*\}\s*from\s*"next\/font\/google"/);
  assert.match(layoutSource, /const\s+inter\s*=\s*Inter\(/);
  assert.match(layoutSource, /const\s+manrope\s*=\s*Manrope\(/);
  assert.doesNotMatch(layoutSource, /Geist/);
  assert.doesNotMatch(layoutSource, /Geist_Mono/);
});

test("logo uses solid blue wave shapes instead of blue stroke outlines", () => {
  assert.match(logoSource, /fill="#1E6BFF"/);
  assert.doesNotMatch(logoSource, /stroke="#1E6BFF"/);
});

test("globals define stitch v2 shell tokens for surfaces and typography", () => {
  assert.match(globalsSource, /--stitch-shell-backdrop:/);
  assert.match(globalsSource, /--stitch-shell-panel:/);
  assert.match(globalsSource, /--stitch-surface-container:/);
  assert.match(globalsSource, /--stitch-outline:/);
  assert.match(globalsSource, /--stitch-inverse-surface:/);
  assert.match(globalsSource, /--stitch-shell-rail:/);
  assert.match(globalsSource, /--stitch-shell-shadow:/);
  assert.match(globalsSource, /\.font-stitch-headline/);
  assert.match(globalsSource, /\.font-stitch-body/);
  assert.match(globalsSource, /\.material-symbols-outlined/);
});

test("shared stitch v2 primitives exist as dedicated component files", () => {
  const componentPaths = [
    "../components/stitch-v2/shell-header.tsx",
    "../components/stitch-v2/shell-sidebar.tsx",
    "../components/stitch-v2/page-hero.tsx",
    "../components/stitch-v2/surface-card.tsx",
    "../components/stitch-v2/status-chip.tsx",
    "../components/stitch-v2/empty-state-panel.tsx",
    "../components/stitch-v2/shell-action.tsx",
    "../components/stitch-v2/material-symbol.tsx",
  ];

  componentPaths.forEach((path) => {
    assert.equal(existsSync(new URL(path, import.meta.url)), true, `${path} should exist`);
  });
});

test("shell header and sidebar use material symbols and stitch-style action surfaces", () => {
  assert.match(shellHeaderSource, /MaterialSymbol/);
  assert.match(shellHeaderSource, /ShellAction/);
  assert.match(shellHeaderSource, /Publish|导出|完成/);
  assert.match(shellSidebarSource, /MaterialSymbol/);
  assert.match(shellSidebarSource, /ShellAction/);
});
