import test from "node:test";
import assert from "node:assert/strict";

import {
  buildContextSections,
  type ContextSection,
} from "../lib/context-panel.ts";
import type { CourseDraft } from "../lib/api/course-drafts.ts";
import type { RunSession } from "../lib/api/runs.ts";
import type { ReviewSummary } from "../lib/api/artifacts.ts";

function pickSection(sections: ContextSection[], title: string): ContextSection {
  const section = sections.find((candidate) => candidate.title === title);
  assert.ok(section, `expected to find section ${title}`);
  return section;
}

test("buildContextSections renders existing draft, run, and review data", () => {
  const draft: CourseDraft = {
    id: "draft-123",
    course_id: "db-course-123",
    book_title: "数据库系统概论",
    course_url: "https://example.com/course",
    runtime_ready: true,
    config: {
      draft_id: "draft-123",
      template: {
        id: "interview",
        name: "面试强化",
        description: "强调术语和问答",
        expected_outputs: ["03-面试问答.md", "global/interview_index.md"],
      },
      content_density: "light",
      review_mode: "light",
      review_enabled: false,
      export_package: true,
      provider: "openai_compatible",
      base_url: "https://draft.example.com/v1",
      simple_model: "draft-simple",
      complex_model: "draft-complex",
      timeout_seconds: 180,
    },
    detected: {
      course_name: "数据库系统概论",
      textbook_title: "数据库系统概论",
      chapter_count: 12,
      asset_completeness: 0.75,
    },
    input_slots: [
      { kind: "subtitle", label: "字幕", supported: true, count: 2 },
      { kind: "slides", label: "课件", supported: false, count: 0 },
    ],
  };

  const run: RunSession = {
    id: "run-123",
    draft_id: "draft-123",
    course_id: "db-course-123",
    status: "running",
    backend: "run-backend",
    run_kind: "chapter",
    hosted: true,
    base_url: "https://run.example.com/v1",
    simple_model: "run-simple",
    complex_model: "run-complex",
    timeout_seconds: 180,
    target_output: "interview_knowledge_base",
    review_enabled: false,
    review_mode: "light",
    stages: [
      { name: "pack_plan", status: "completed" },
      { name: "write_interview_qa", status: "running" },
      { name: "build_interview_index", status: "pending" },
    ],
    last_error: null,
  };

  const reviewSummary: ReviewSummary = {
    course_id: "db-course-123",
    report_count: 2,
    issue_count: 5,
    reports: [
      {
        path: "chapters/ch1/review_report.json",
        status: "needs_attention",
        issues: ["missing glossary"],
      },
      {
        path: "chapters/ch2/review_report.json",
        status: "passed",
        issues: [],
      },
    ],
  };

  const sections = buildContextSections({
    draft,
    run,
    reviewSummary,
  });

  const course = pickSection(sections, "课程摘要");
  assert.deepEqual(course.items.slice(0, 4), [
    "教材：数据库系统概论",
    "章节数：12",
    "素材完整度：75%",
    "输入素材：字幕 2",
  ]);

  const template = pickSection(sections, "模板摘要");
  assert.deepEqual(template.items.slice(0, 5), [
    "模板：面试强化",
    "内容密度：light",
    "Review：light",
    "后端：run-backend",
    "模型：简单 run-simple / 复杂 run-complex",
  ]);

  const runtime = pickSection(sections, "运行摘要");
  assert.deepEqual(runtime.items.slice(0, 4), [
    "状态：running",
    "目标产物：interview_knowledge_base",
    "已完成阶段：1/3",
    "当前阶段：write_interview_qa",
  ]);
});

test("buildContextSections shows asset completeness as a percentage without scaling percent input", () => {
  const draft: CourseDraft = {
    id: "draft-123",
    course_id: "db-course-123",
    book_title: "数据库系统概论",
    course_url: "https://example.com/course",
    runtime_ready: true,
    config: null,
    detected: {
      course_name: "数据库系统概论",
      textbook_title: "数据库系统概论",
      chapter_count: 12,
      asset_completeness: 60,
    },
    input_slots: [],
  };

  const sections = buildContextSections({ draft });

  const course = pickSection(sections, "课程摘要");
  assert.ok(course.items.includes("素材完整度：60%"));
});

test("buildContextSections surfaces active runtime backend and models even without draft config", () => {
  const draft: CourseDraft = {
    id: "draft-456",
    course_id: "db-course-456",
    book_title: "数据库系统概论",
    course_url: null,
    runtime_ready: true,
    config: null,
    detected: {
      course_name: "数据库系统概论",
      textbook_title: "数据库系统概论",
      chapter_count: 3,
      asset_completeness: 80,
    },
    input_slots: [],
  };

  const run: RunSession = {
    id: "run-456",
    draft_id: "draft-456",
    course_id: "db-course-456",
    status: "running",
    backend: "openai_compatible",
    run_kind: "chapter",
    hosted: true,
    base_url: "https://api.example.com/v1",
    simple_model: "gpt-5.4-mini",
    complex_model: "gpt-5.4",
    timeout_seconds: 240,
    target_output: "standard_knowledge_pack",
    review_enabled: false,
    review_mode: null,
    stages: [{ name: "ingest", status: "running" }],
    last_error: null,
  };

  const sections = buildContextSections({ draft, run });
  const template = pickSection(sections, "模板摘要");

  assert.deepEqual(template.items, [
    "模板：沿用当前运行配置",
    "内容密度：待确认",
    "Review：未配置",
    "后端：openai_compatible",
    "模型：简单 gpt-5.4-mini / 复杂 gpt-5.4",
  ]);
});

test("buildContextSections falls back to placeholder guidance when no data exists", () => {
  const sections = buildContextSections({});

  assert.deepEqual(sections, [
    {
      title: "课程摘要",
      items: ["这里会展示教材、章节数、素材完整度和识别出的课程元信息。"],
    },
    {
      title: "模板摘要",
      items: ["当前输出模板、review 策略与导出规则会在这里聚合展示。"],
    },
    {
      title: "运行摘要",
      items: ["运行开始后，这里将显示本次任务的关键信息与执行摘要。"],
    },
  ]);
});
