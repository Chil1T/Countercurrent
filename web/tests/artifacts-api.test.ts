import test from "node:test";
import assert from "node:assert/strict";

import { buildExportUrl } from "../lib/api/artifacts.ts";

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
