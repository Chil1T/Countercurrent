import test from "node:test";
import assert from "node:assert/strict";

import { buildProductHref, buildProductNav } from "../lib/product-nav.ts";

test("product nav preserves draft context on input and config routes", () => {
  const context = {
    draftId: "draft-1234",
    courseId: "course-1234",
    runId: "run-1234",
  };

  assert.equal(
    buildProductHref("input", context),
    "/courses/new/input?draftId=draft-1234&courseId=course-1234&runId=run-1234",
  );
  assert.equal(
    buildProductHref("config", context),
    "/courses/new/config?draftId=draft-1234&courseId=course-1234&runId=run-1234",
  );
});

test("product nav uses real run and course routes instead of demo placeholders", () => {
  const context = {
    draftId: "draft-1234",
    courseId: "course-1234",
    runId: "run-1234",
  };

  assert.equal(
    buildProductHref("run", context),
    "/runs/run-1234?draftId=draft-1234&courseId=course-1234",
  );
  assert.equal(
    buildProductHref("results", context),
    "/courses/course-1234/results?draftId=draft-1234&runId=run-1234",
  );
});

test("product nav falls back to root workbenches when no run or course exists", () => {
  const nav = buildProductNav({
    draftId: "draft-1234",
    courseId: null,
    runId: null,
  });

  assert.equal(nav[3]?.href, "/runs?draftId=draft-1234");
  assert.equal(nav[4]?.href, "/courses/results?draftId=draft-1234");
});
