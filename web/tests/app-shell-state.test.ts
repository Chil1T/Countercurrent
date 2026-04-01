import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { buildAppShellState } from "../lib/app-shell-state.ts";

test("input page now routes run and result navigation to empty workbenches", () => {
  const state = buildAppShellState("/courses/new/input", new URLSearchParams());

  assert.equal(state.navItems[2]?.href, "/runs");
  assert.equal(state.navItems[2]?.enabled, true);
  assert.equal(state.navItems[3]?.href, "/courses/results");
  assert.equal(state.navItems[3]?.enabled, true);
});

test("config page preserves the active draft id in the config link", () => {
  const state = buildAppShellState(
    "/courses/new/config",
    new URLSearchParams("draftId=draft-1234"),
  );

  assert.equal(state.navItems[0]?.href, "/courses/new/input?draftId=draft-1234");
  assert.equal(state.navItems[1]?.href, "/courses/new/config?draftId=draft-1234");
  assert.equal(state.navItems[2]?.href, "/runs?draftId=draft-1234");
  assert.equal(state.navItems[3]?.href, "/courses/results?draftId=draft-1234");
});

test("config page keeps run and result links available when run context exists", () => {
  const state = buildAppShellState(
    "/courses/new/config",
    new URLSearchParams("draftId=draft-1234&runId=run-5678&courseId=database-course"),
  );

  assert.equal(
    state.navItems[0]?.href,
    "/courses/new/input?draftId=draft-1234&runId=run-5678&courseId=database-course",
  );
  assert.equal(
    state.navItems[1]?.href,
    "/courses/new/config?draftId=draft-1234&runId=run-5678&courseId=database-course",
  );
  assert.equal(
    state.navItems[2]?.href,
    "/runs/run-5678?draftId=draft-1234&courseId=database-course",
  );
  assert.equal(state.navItems[2]?.enabled, true);
  assert.equal(
    state.navItems[3]?.href,
    "/courses/database-course/results?draftId=draft-1234&runId=run-5678",
  );
  assert.equal(state.navItems[3]?.enabled, true);
});

test("empty run and result routes preserve draft context without inventing preview ids", () => {
  const runState = buildAppShellState(
    "/runs",
    new URLSearchParams("draftId=draft-1234&courseId=database-course"),
  );
  const resultsState = buildAppShellState(
    "/courses/results",
    new URLSearchParams("draftId=draft-1234&courseId=database-course"),
  );

  assert.equal(runState.navItems[2]?.href, "/runs?draftId=draft-1234&courseId=database-course");
  assert.equal(runState.navItems[3]?.href, "/courses/database-course/results?draftId=draft-1234");
  assert.equal(resultsState.navItems[2]?.href, "/runs?draftId=draft-1234&courseId=database-course");
  assert.equal(resultsState.navItems[3]?.href, "/courses/database-course/results?draftId=draft-1234");
});

test("run page keeps the real run route instead of demo placeholders", () => {
  const state = buildAppShellState(
    "/runs/run-4b4e2137",
    new URLSearchParams("draftId=draft-1234&courseId=database-course"),
  );

  assert.equal(
    state.navItems[2]?.href,
    "/runs/run-4b4e2137?draftId=draft-1234&courseId=database-course",
  );
  assert.equal(state.navItems[2]?.enabled, true);
  assert.equal(
    state.navItems[0]?.href,
    "/courses/new/input?draftId=draft-1234&runId=run-4b4e2137&courseId=database-course",
  );
  assert.equal(
    state.navItems[1]?.href,
    "/courses/new/config?draftId=draft-1234&runId=run-4b4e2137&courseId=database-course",
  );
  assert.equal(
    state.navItems[3]?.href,
    "/courses/database-course/results?draftId=draft-1234&runId=run-4b4e2137",
  );
  assert.equal(state.navItems[3]?.enabled, true);
});

test("results page keeps the real course route instead of demo placeholders", () => {
  const state = buildAppShellState(
    "/courses/database-course/results",
    new URLSearchParams("draftId=draft-1234&runId=run-4b4e2137"),
  );

  assert.equal(state.courseLabel, "database-course");
  assert.equal(
    state.navItems[0]?.href,
    "/courses/new/input?draftId=draft-1234&runId=run-4b4e2137&courseId=database-course",
  );
  assert.equal(
    state.navItems[1]?.href,
    "/courses/new/config?draftId=draft-1234&runId=run-4b4e2137&courseId=database-course",
  );
  assert.equal(state.navItems[2]?.href, "/runs/run-4b4e2137?draftId=draft-1234&courseId=database-course");
  assert.equal(state.navItems[2]?.enabled, true);
  assert.equal(
    state.navItems[3]?.href,
    "/courses/database-course/results?draftId=draft-1234&runId=run-4b4e2137",
  );
  assert.equal(state.navItems[3]?.enabled, true);
});

test("shell and overview pages do not hardcode demo run or result routes", () => {
  const appShellSource = readFileSync(
    resolve(import.meta.dirname, "../components/app-shell.tsx"),
    "utf-8",
  );
  const homeSource = readFileSync(
    resolve(import.meta.dirname, "../app/page.tsx"),
    "utf-8",
  );

  assert.equal(appShellSource.includes("/runs/demo"), false);
  assert.equal(appShellSource.includes("/courses/demo/results"), false);
  assert.equal(appShellSource.includes("demo-course"), false);
  assert.equal(homeSource.includes("/runs/demo"), false);
  assert.equal(homeSource.includes("/courses/demo/results"), false);
});

test("app shell uses top sticky navigation with a fixed right summary rail", () => {
  const appShellSource = readFileSync(
    resolve(import.meta.dirname, "../components/app-shell.tsx"),
    "utf-8",
  );

  assert.equal(appShellSource.includes("ShellHeader"), true);
  assert.equal(appShellSource.includes("ShellSidebar"), true);
  assert.equal(appShellSource.includes("PageHero"), true);
  assert.equal(appShellSource.includes("SurfaceCard"), true);
  assert.equal(appShellSource.includes("xl:grid-cols-[240px_minmax(0,1fr)_320px]"), true);
  assert.equal(appShellSource.includes("sticky top-24"), true);
  assert.equal(appShellSource.includes("打开阶段导航"), false);
  assert.equal(appShellSource.includes("打开摘要面板"), false);
});

test("input workbench uses a dedicated file picker button and hidden input", () => {
  const inputWorkbenchSource = readFileSync(
    resolve(import.meta.dirname, "../components/input/course-draft-workbench.tsx"),
    "utf-8",
  );

  assert.equal(inputWorkbenchSource.includes("subtitleFileInputRef.current?.click()"), true);
  assert.equal(inputWorkbenchSource.includes('id="subtitle-files-input"'), true);
});

test("input and config side columns use sticky summaries in the first UX pass", () => {
  const inputWorkbenchSource = readFileSync(
    resolve(import.meta.dirname, "../components/input/course-draft-workbench.tsx"),
    "utf-8",
  );
  const configWorkbenchSource = readFileSync(
    resolve(import.meta.dirname, "../components/config/template-config-workbench.tsx"),
    "utf-8",
  );

  assert.equal(inputWorkbenchSource.includes("xl:self-start xl:sticky xl:top-24"), true);
  assert.equal(configWorkbenchSource.includes("xl:self-start xl:sticky xl:top-24"), true);
  assert.equal(configWorkbenchSource.includes("2xl:self-start 2xl:sticky 2xl:top-24"), true);
});

test("run page only exposes results shortcut after completion", () => {
  const runWorkbenchSource = readFileSync(
    resolve(import.meta.dirname, "../components/run/run-session-workbench.tsx"),
    "utf-8",
  );

  assert.equal(runWorkbenchSource.includes('run.status === "completed" ? ('), true);
  assert.equal(runWorkbenchSource.includes("查看结果页"), true);
});

test("config page only renders the active default provider card and uses rounded select styling", () => {
  const configWorkbenchSource = readFileSync(
    resolve(import.meta.dirname, "../components/config/template-config-workbench.tsx"),
    "utf-8",
  );

  assert.equal(configWorkbenchSource.includes("activeDefaultProviderSettings"), true);
  assert.equal(configWorkbenchSource.includes('defaultProvider === "heuristic" ? ('), true);
  assert.equal(configWorkbenchSource.includes("HOSTED_PROVIDERS.map"), false);
  assert.equal(configWorkbenchSource.includes("appearance-none"), true);
});
