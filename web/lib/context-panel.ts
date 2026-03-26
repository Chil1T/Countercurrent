import type { ReviewSummary } from "./api/artifacts";
import type { CourseDraft } from "./api/course-drafts";
import type { RunSession } from "./api/runs";

export type ContextSection = {
  title: string;
  items: string[];
};

function formatAssetCompleteness(assetCompleteness: number): string {
  const percentage = assetCompleteness > 1 ? assetCompleteness : assetCompleteness * 100;
  return `${Math.round(percentage)}%`;
}

function buildCourseItems(draft?: CourseDraft | null): string[] {
  if (!draft) {
    return ["这里会展示教材、章节数、素材完整度和识别出的课程元信息。"];
  }

  const assetItems = draft.input_slots
    .filter((slot) => slot.count > 0)
    .map((slot) => `${slot.label} ${slot.count}`);

  return [
    `教材：${draft.book_title}`,
    `章节数：${draft.detected.chapter_count ?? "待识别"}`,
    `素材完整度：${formatAssetCompleteness(draft.detected.asset_completeness)}`,
    `输入素材：${assetItems.join(" / ") || "暂无"}`,
    `运行就绪：${draft.runtime_ready ? "是" : "否"}`,
  ];
}

function buildTemplateItems(
  draft?: CourseDraft | null,
  run?: RunSession | null,
): string[] {
  const config = draft?.config;
  if (!config && !run) {
    return ["当前输出模板、review 策略与导出规则会在这里聚合展示。"];
  }

  if (!config && run) {
    return [
      "模板：沿用当前运行配置",
      "内容密度：待确认",
      "Review：未配置",
      `后端：${run.backend}`,
      `模型：简单 ${run.simple_model ?? "未配置"} / 复杂 ${run.complex_model ?? "未配置"}`,
    ];
  }

  if (!config) {
    return ["当前输出模板、review 策略与导出规则会在这里聚合展示。"];
  }

  return [
    `模板：${config.template.name}`,
    `内容密度：${config.content_density}`,
    `Review：${config.review_mode}`,
    `后端：${run?.backend ?? config.provider ?? "heuristic"}`,
    `模型：简单 ${run?.simple_model ?? config.simple_model ?? "未配置"} / 复杂 ${
      run?.complex_model ?? config.complex_model ?? "未配置"
    }`,
  ];
}

function buildRuntimeItems(
  run?: RunSession | null,
): string[] {
  if (!run) {
    return ["运行开始后，这里将显示本次任务的关键信息与执行摘要。"];
  }

  const completedCount = run.stages.filter((stage) => stage.status === "completed").length;
  const currentStage =
    run.stages.find((stage) => stage.status === "running")?.name ??
    run.stages.find((stage) => stage.status === "failed")?.name ??
    run.stages.find((stage) => stage.status === "pending")?.name ??
    "无";

  const items = [
    `状态：${run.status}`,
    `目标产物：${run.target_output ?? "未配置"}`,
    `已完成阶段：${completedCount}/${run.stages.length}`,
    `当前阶段：${currentStage}`,
  ];

  if (run.last_error) {
    items.push(`最近错误：${run.last_error}`);
  }

  return items;
}

export function buildContextSections({
  draft,
  run,
}: {
  draft?: CourseDraft | null;
  run?: RunSession | null;
  reviewSummary?: ReviewSummary | null;
}): ContextSection[] {
  return [
    {
      title: "课程摘要",
      items: buildCourseItems(draft),
    },
    {
      title: "模板摘要",
      items: buildTemplateItems(draft, run),
    },
    {
      title: "运行摘要",
      items: buildRuntimeItems(run),
    },
  ];
}
