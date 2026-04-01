import type {
  CourseResultsContext,
  RunLogPreview,
  RunSession,
} from "@/lib/api/runs";
import type {
  ArtifactContent,
  ArtifactNode,
  ReviewSummary,
} from "@/lib/api/artifacts";

export type PreviewScenario = "running" | "completed";

export type RunWorkbenchPreview = {
  scenario: PreviewScenario;
  run: RunSession;
  runLog: RunLogPreview;
};

export type ResultsWorkbenchPreview = {
  scenario: PreviewScenario;
  courseId: string;
  runId: string | null;
  nodes: ArtifactNode[];
  contentByPath: Record<string, ArtifactContent>;
  reviewSummary: ReviewSummary;
  context: CourseResultsContext;
  run: RunSession | null;
};

export const PREVIEW_RUN_ID = "preview-run";
export const PREVIEW_COURSE_ID = "preview";
export const PREVIEW_DRAFT_ID = "preview-draft";

function buildPreviewRun(status: "running" | "completed"): RunSession {
  return {
    id: PREVIEW_RUN_ID,
    draft_id: PREVIEW_DRAFT_ID,
    course_id: PREVIEW_COURSE_ID,
    created_at: "2026-04-01T10:00:00+08:00",
    status,
    run_kind: "chapter",
    backend: "openai_compatible",
    hosted: true,
    base_url: "https://api.preview.local/v1",
    simple_model: "gpt-5.4-mini",
    complex_model: "gpt-5.4",
    timeout_seconds: 300,
    target_output: "interview_knowledge_base",
    review_enabled: true,
    review_mode: "light",
    stages:
      status === "running"
        ? [
            { name: "build_blueprint", status: "completed" },
            { name: "ingest", status: "completed" },
            { name: "curriculum_anchor", status: "completed" },
            { name: "gap_fill", status: "running" },
            { name: "pack_plan", status: "pending" },
          ]
        : [
            { name: "build_blueprint", status: "completed" },
            { name: "ingest", status: "completed" },
            { name: "curriculum_anchor", status: "completed" },
            { name: "gap_fill", status: "completed" },
            { name: "pack_plan", status: "completed" },
            { name: "write_interview_qa", status: "completed" },
            { name: "review", status: "completed" },
          ],
    chapter_progress:
      status === "running"
        ? [
            {
              chapter_id: "chapter-01",
              status: "completed",
              current_step: null,
              completed_step_count: 6,
              total_step_count: 6,
              export_ready: true,
            },
            {
              chapter_id: "chapter-02",
              status: "running",
              current_step: "write_interview_qa",
              completed_step_count: 4,
              total_step_count: 6,
              export_ready: false,
            },
            {
              chapter_id: "chapter-03",
              status: "running",
              current_step: "write_terms",
              completed_step_count: 3,
              total_step_count: 6,
              export_ready: false,
            },
            {
              chapter_id: "chapter-04",
              status: "pending",
              current_step: null,
              completed_step_count: 0,
              total_step_count: 6,
              export_ready: false,
            },
          ]
        : [
            {
              chapter_id: "chapter-01",
              status: "completed",
              current_step: null,
              completed_step_count: 6,
              total_step_count: 6,
              export_ready: true,
            },
            {
              chapter_id: "chapter-02",
              status: "completed",
              current_step: null,
              completed_step_count: 6,
              total_step_count: 6,
              export_ready: true,
            },
            {
              chapter_id: "chapter-03",
              status: "completed",
              current_step: null,
              completed_step_count: 6,
              total_step_count: 6,
              export_ready: true,
            },
          ],
    last_error: null,
  };
}

function buildPreviewRunLog(status: "running" | "completed"): RunLogPreview {
  return {
    run_id: PREVIEW_RUN_ID,
    available: true,
    cursor: 3,
    truncated: false,
    content:
      status === "running"
        ? [
            "[10:00:12] blueprint completed",
            "[10:00:35] chapter-02 write_interview_qa running",
            "[10:00:37] chapter-03 write_terms running",
          ].join("\n")
        : [
            "[10:00:12] blueprint completed",
            "[10:01:48] all chapter writers completed",
            "[10:02:10] review reports persisted",
          ].join("\n"),
  };
}

export function resolvePreviewScenario(
  input: string | undefined,
  fallback: PreviewScenario,
): PreviewScenario {
  return input === "running" || input === "completed" ? input : fallback;
}

export function buildRunWorkbenchPreview(
  scenario: PreviewScenario,
): RunWorkbenchPreview {
  const status = scenario === "completed" ? "completed" : "running";
  return {
    scenario,
    run: buildPreviewRun(status),
    runLog: buildPreviewRunLog(status),
  };
}

export function buildResultsWorkbenchPreview(
  scenario: PreviewScenario,
): ResultsWorkbenchPreview {
  const runStatus = scenario === "completed" ? "completed" : "running";
  const latestRun = buildPreviewRun(runStatus);
  const nodes: ArtifactNode[] =
    scenario === "completed"
      ? [
          { path: "chapters/chapter-01/notebooklm/01-lecture-note.md", kind: "file", size: 14200 },
          { path: "chapters/chapter-01/intermediate/pack_plan.json", kind: "file", size: 2200 },
          { path: "chapters/chapter-02/notebooklm/01-lecture-note.md", kind: "file", size: 13800 },
          { path: "chapters/chapter-02/notebooklm/03-qa.md", kind: "file", size: 7200 },
          { path: "chapters/chapter-03/notebooklm/02-terms.md", kind: "file", size: 6400 },
          { path: "global/interview_index.md", kind: "file", size: 3200 },
          { path: "runtime/runtime_state.json", kind: "file", size: 1800 },
        ]
      : [
          { path: "chapters/chapter-01/notebooklm/01-lecture-note.md", kind: "file", size: 14200 },
          { path: "chapters/chapter-01/intermediate/pack_plan.json", kind: "file", size: 2200 },
          { path: "chapters/chapter-02/intermediate/pack_plan.json", kind: "file", size: 2100 },
          { path: "runtime/runtime_state.json", kind: "file", size: 1500 },
        ];

  const contentByPath: Record<string, ArtifactContent> = {};
  for (const node of nodes) {
    contentByPath[node.path] = {
      path: node.path,
      kind: "text/markdown",
      content:
        node.path === "runtime/runtime_state.json"
          ? `{\n  "course_id": "${PREVIEW_COURSE_ID}",\n  "status": "${runStatus}"\n}`
          : `# ${node.path.split("/").at(-1) ?? "preview"}\n\n这是用于 UI 预览态的示例内容，用来检查布局、树结构和排版。`,
    };
  }

  return {
    scenario,
    courseId: PREVIEW_COURSE_ID,
    runId: PREVIEW_RUN_ID,
    nodes,
    contentByPath,
    reviewSummary: {
      course_id: PREVIEW_COURSE_ID,
      report_count: scenario === "completed" ? 3 : 1,
      issue_count: scenario === "completed" ? 2 : 1,
      reports: [
        {
          path: "chapters/chapter-02/review_report.json",
          status: scenario === "completed" ? "passed" : "needs_attention",
          issues:
            scenario === "completed"
              ? ["cross-link wording needs polish"]
              : ["writer output still running"],
        },
      ],
    },
    context: {
      course_id: PREVIEW_COURSE_ID,
      latest_run: latestRun,
    },
    run: latestRun,
  };
}
