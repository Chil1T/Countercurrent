import test from "node:test";
import assert from "node:assert/strict";

import {
  buildArtifactTree,
  buildResultsSnapshotTree,
  buildResultsSnapshotSelection,
  getResultsTreeSelectionAncestors,
  getArtifactDisplayName,
  getArtifactGroupLabel,
  getArtifactTreeCardClass,
  isArtifactTreeLoading,
} from "../lib/results-view.ts";

test("artifact tree displays only the final file name", () => {
  assert.equal(
    getArtifactDisplayName("chapters/chapter-01/notebooklm/03-面试问答.md"),
    "03-面试问答.md",
  );
  assert.equal(getArtifactDisplayName("course_blueprint.json"), "course_blueprint.json");
});

test("artifact paths map to stable visual groups", () => {
  assert.equal(
    getArtifactGroupLabel("chapters/chapter-01/notebooklm/03-面试问答.md"),
    "章节产物",
  );
  assert.equal(
    getArtifactGroupLabel("chapters/chapter-01/intermediate/normalized_transcript.json"),
    "中间数据",
  );
  assert.equal(getArtifactGroupLabel("global/interview_index.md"), "全局汇总");
  assert.equal(getArtifactGroupLabel("chapters/chapter-01/review_report.json"), "Review");
  assert.equal(getArtifactGroupLabel("course_blueprint.json"), "运行文件");
});

test("artifact cards stay neutral until selected", () => {
  assert.match(
    getArtifactTreeCardClass("chapters/chapter-01/notebooklm/03-面试问答.md", false),
    /bg-stone-50/,
  );
  assert.match(
    getArtifactTreeCardClass("chapters/chapter-01/intermediate/topic_anchor_map.json", false),
    /text-stone-700/,
  );
  assert.match(
    getArtifactTreeCardClass("course_blueprint.json", true),
    /bg-stone-900 text-white/,
  );
});

test("legacy artifact tree still groups final and intermediate files for compatibility helpers", () => {
  const tree = buildArtifactTree([
    {
      path: "chapters/chapter-01/notebooklm/03-面试问答.md",
      kind: "file",
      size: 12,
    },
    {
      path: "chapters/chapter-01/intermediate/normalized_transcript.json",
      kind: "json",
      size: 34,
    },
    {
      path: "global/interview_index.md",
      kind: "file",
      size: 56,
    },
  ]);

  assert.deepEqual(tree[0], {
    key: "chapter",
    label: "章节产物",
    children: [
      {
        key: "chapter-01",
        label: "chapter-01",
        children: [
          {
            key: "chapter-01:final",
            label: "最终产物",
            children: [
              {
                key: "chapters/chapter-01/notebooklm/03-面试问答.md",
                path: "chapters/chapter-01/notebooklm/03-面试问答.md",
                label: "03-面试问答.md",
              },
            ],
          },
          {
            key: "chapter-01:intermediate",
            label: "中间数据",
            children: [
              {
                key: "chapters/chapter-01/intermediate/normalized_transcript.json",
                path: "chapters/chapter-01/intermediate/normalized_transcript.json",
                label: "normalized_transcript.json",
              },
            ],
          },
        ],
      },
    ],
  });
  assert.deepEqual(tree[1], {
    key: "global",
    label: "全局汇总",
    children: [
      {
        key: "global/interview_index.md",
        path: "global/interview_index.md",
        label: "interview_index.md",
      },
    ],
  });
});

test("artifact loading depends on run status instead of tree emptiness", () => {
  assert.equal(isArtifactTreeLoading("running"), true);
  assert.equal(isArtifactTreeLoading("completed"), false);
  assert.equal(isArtifactTreeLoading("failed"), false);
  assert.equal(isArtifactTreeLoading(null), false);
});

test("results snapshot tree groups historical courses and current course runs while keeping only markdown files", () => {
  const tree = buildResultsSnapshotTree({
    current_course_id: "database-course",
    current_course_runs: [
      {
        run_id: "run-current-001",
        chapters: [
          {
            chapter_id: "chapter-01",
            files: [
              {
                path: "chapters/chapter-01/notebooklm/01-精讲.md",
                kind: "markdown",
                size: 12,
              },
            ],
          },
        ],
      },
    ],
    historical_courses: [
      {
        course_id: "operating-systems-course",
        runs: [
          {
            run_id: "run-history-001",
            chapters: [
              {
                chapter_id: "chapter-02",
                files: [
                  {
                    path: "chapters/chapter-02/notebooklm/01-精讲.md",
                    kind: "markdown",
                    size: 24,
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  });

  assert.equal(tree[0]?.label, "过去课程产物");
  assert.equal(tree[1]?.label, "当前课程产物");
  assert.equal(tree[1]?.children[0]?.key, "run-current-001");
});

test("results snapshot tree section labels follow the selected locale", () => {
  const tree = buildResultsSnapshotTree(
    {
      current_course_id: "database-course",
      current_course_runs: [],
      historical_courses: [],
    },
    null,
    "en",
  );

  assert.equal(tree[0]?.label, "Past Course Outputs");
  assert.equal(tree[1]?.label, "Current Course Outputs");
});

test("results snapshot selection ancestors expand course, run, and chapter folders", () => {
  const selection = buildResultsSnapshotSelection({
    sourceCourseId: "__current__",
    runId: "run-current-001",
    path: "chapters/chapter-01/notebooklm/01-精讲.md",
  });

  assert.deepEqual(getResultsTreeSelectionAncestors(selection), [
    "current-course",
    "run-current-001",
    "run-current-001:chapter-01",
  ]);
});
