import test from "node:test";
import assert from "node:assert/strict";

import { shouldRefreshArtifactsOnRunUpdate } from "../lib/results-refresh.ts";
import type { RunSession } from "../lib/api/runs.ts";

function makeRun(overrides?: Partial<RunSession>): RunSession {
  return {
    id: "run-1234",
    draft_id: "draft-1234",
    course_id: "course-1234",
    status: "running",
    run_kind: "chapter",
    backend: "openai_compatible",
    hosted: true,
    base_url: "https://example.test/v1/chat/completions",
    simple_model: "mini",
    complex_model: "large",
    timeout_seconds: 180,
    target_output: "standard_knowledge_pack",
    review_enabled: false,
    review_mode: "light",
    stages: [
      { name: "build_blueprint", status: "completed" },
      { name: "ingest", status: "running" },
    ],
    last_error: null,
    ...overrides,
  };
}

test("refreshes artifacts when run status changes", () => {
  const previousRun = makeRun({ status: "running" });
  const nextRun = makeRun({ status: "completed" });

  assert.equal(shouldRefreshArtifactsOnRunUpdate(previousRun, nextRun), true);
});

test("refreshes artifacts when stage progress changes", () => {
  const previousRun = makeRun();
  const nextRun = makeRun({
    stages: [
      { name: "build_blueprint", status: "completed" },
      { name: "ingest", status: "completed" },
    ],
  });

  assert.equal(shouldRefreshArtifactsOnRunUpdate(previousRun, nextRun), true);
});

test("skips artifact refresh when run update is unchanged", () => {
  const previousRun = makeRun();
  const nextRun = makeRun();

  assert.equal(shouldRefreshArtifactsOnRunUpdate(previousRun, nextRun), false);
});
