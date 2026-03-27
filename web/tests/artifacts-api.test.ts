import test from "node:test";
import assert from "node:assert/strict";

import { buildExportUrl } from "../lib/api/artifacts.ts";
import type { RunSession } from "../lib/api/runs.ts";

test("buildExportUrl appends a cache-bust token when provided", () => {
  assert.equal(
    buildExportUrl("demo-course", "tree-42"),
    "http://127.0.0.1:8000/courses/demo-course/export?v=tree-42",
  );
});

test("buildExportUrl keeps the base export path when no cache-bust token is provided", () => {
  assert.equal(
    buildExportUrl("demo-course"),
    "http://127.0.0.1:8000/courses/demo-course/export",
  );
});

test("buildExportUrl appends export filters when provided", () => {
  assert.equal(
    buildExportUrl("demo-course", {
      cacheBust: "tree-99",
      completedChaptersOnly: true,
      finalOutputsOnly: true,
    }),
    "http://127.0.0.1:8000/courses/demo-course/export?v=tree-99&completed_chapters_only=true&final_outputs_only=true",
  );
});

test("RunSession type includes chapter_progress export readiness fields", () => {
  const run: RunSession = {
    id: "run-123",
    draft_id: "draft-123",
    course_id: "demo-course",
    status: "running",
    run_kind: "chapter",
    backend: "heuristic",
    hosted: false,
    base_url: null,
    simple_model: null,
    complex_model: null,
    timeout_seconds: null,
    target_output: "interview_knowledge_base",
    review_enabled: true,
    review_mode: "standard",
    stages: [{ name: "ingest", status: "completed" }],
    chapter_progress: [
      {
        chapter_id: "chapter-01",
        status: "completed",
        current_step: null,
        completed_step_count: 9,
        total_step_count: 9,
        export_ready: true,
      },
    ],
    last_error: null,
  };

  assert.equal(run.chapter_progress[0]?.export_ready, true);
  assert.equal(run.chapter_progress[0]?.completed_step_count, 9);
});
