import test from "node:test";
import assert from "node:assert/strict";

import {
  buildExportUrl,
  buildGlobalResultsSnapshotContentUrl,
  buildResultsSnapshotContentUrl,
} from "../lib/api/artifacts.ts";
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

test("buildResultsSnapshotContentUrl encodes source course, run id, and path", () => {
  assert.equal(
    buildResultsSnapshotContentUrl("database-course", {
      sourceCourseId: "operating-systems-course",
      runId: "run-history-001",
      path: "chapters/chapter-02/notebooklm/01-精讲.md",
    }),
    "http://127.0.0.1:8000/courses/database-course/results-snapshot/content?source_course_id=operating-systems-course&run_id=run-history-001&path=chapters%2Fchapter-02%2Fnotebooklm%2F01-%E7%B2%BE%E8%AE%B2.md",
  );
});

test("buildGlobalResultsSnapshotContentUrl targets the course-agnostic snapshot endpoint", () => {
  assert.equal(
    buildGlobalResultsSnapshotContentUrl({
      sourceCourseId: "operating-systems-course",
      runId: "run-history-001",
      path: "chapters/chapter-02/notebooklm/01-精讲.md",
    }),
    "http://127.0.0.1:8000/results-snapshot/content?source_course_id=operating-systems-course&run_id=run-history-001&path=chapters%2Fchapter-02%2Fnotebooklm%2F01-%E7%B2%BE%E8%AE%B2.md",
  );
});

test("RunSession type includes chapter_progress export readiness fields", () => {
  const run: RunSession = {
    id: "run-123",
    draft_id: "draft-123",
    course_id: "demo-course",
    created_at: "2026-03-30T12:00:00+00:00",
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
    snapshot_complete: false,
    last_error: null,
  };

  assert.equal(run.chapter_progress[0]?.export_ready, true);
  assert.equal(run.chapter_progress[0]?.completed_step_count, 9);
});
