import test from "node:test";
import assert from "node:assert/strict";

import {
  buildArtifactTree,
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

test("artifact tree nests chapter files under final and intermediate folders", () => {
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
