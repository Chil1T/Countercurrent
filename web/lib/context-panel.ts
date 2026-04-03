import type { ReviewSummary } from "./api/artifacts";
import type { CourseDraft } from "./api/course-drafts";
import type { RunSession } from "./api/runs";
import type { Locale } from "./locale";

export type ContextSection = {
  title: string;
  items: string[];
};

function formatAssetCompleteness(assetCompleteness: number): string {
  const percentage = assetCompleteness > 1 ? assetCompleteness : assetCompleteness * 100;
  return `${Math.round(percentage)}%`;
}

function buildCourseItems(locale: Locale, draft?: CourseDraft | null): string[] {
  if (!draft) {
    return [
      locale === "zh-CN"
        ? "这里会展示教材、章节数、素材完整度和识别出的课程元信息。"
        : "This area shows textbook, chapter count, asset completeness, and detected course metadata.",
    ];
  }

  const assetItems = draft.input_slots
    .filter((slot) => slot.count > 0)
    .map((slot) => `${slot.label} ${slot.count}`);

  return [
    `${locale === "zh-CN" ? "教材" : "Textbook"}: ${draft.book_title}`,
    `${locale === "zh-CN" ? "章节数" : "Chapters"}: ${draft.detected.chapter_count ?? (locale === "zh-CN" ? "待识别" : "Pending")}`,
    `${locale === "zh-CN" ? "素材完整度" : "Asset Completeness"}: ${formatAssetCompleteness(draft.detected.asset_completeness)}`,
    `${locale === "zh-CN" ? "输入素材" : "Input Assets"}: ${assetItems.join(" / ") || (locale === "zh-CN" ? "暂无" : "None")}`,
    `${locale === "zh-CN" ? "运行就绪" : "Runtime Ready"}: ${draft.runtime_ready ? (locale === "zh-CN" ? "是" : "Yes") : (locale === "zh-CN" ? "否" : "No")}`,
  ];
}

function buildTemplateItems(
  locale: Locale,
  draft?: CourseDraft | null,
  run?: RunSession | null,
): string[] {
  const config = draft?.config;
  if (!config && !run) {
    return [
      locale === "zh-CN"
        ? "当前输出模板、review 策略与导出规则会在这里聚合展示。"
        : "The current output template, review policy, and export rules will be summarized here.",
    ];
  }

  if (!config && run) {
    return [
      `${locale === "zh-CN" ? "模板" : "Template"}: ${locale === "zh-CN" ? "沿用当前运行配置" : "Using current run config"}`,
      `${locale === "zh-CN" ? "内容密度" : "Content Density"}: ${locale === "zh-CN" ? "待确认" : "Pending"}`,
      `Review: ${locale === "zh-CN" ? "未配置" : "Not configured"}`,
      `${locale === "zh-CN" ? "后端" : "Backend"}: ${run.backend}`,
      `${locale === "zh-CN" ? "模型" : "Models"}: ${locale === "zh-CN" ? "简单" : "Simple"} ${run.simple_model ?? (locale === "zh-CN" ? "未配置" : "Not configured")} / ${locale === "zh-CN" ? "复杂" : "Complex"} ${run.complex_model ?? (locale === "zh-CN" ? "未配置" : "Not configured")}`,
    ];
  }

  if (!config) {
    return [
      locale === "zh-CN"
        ? "当前输出模板、review 策略与导出规则会在这里聚合展示。"
        : "The current output template, review policy, and export rules will be summarized here.",
    ];
  }

  return [
    `${locale === "zh-CN" ? "模板" : "Template"}: ${config.template.name}`,
    `${locale === "zh-CN" ? "内容密度" : "Content Density"}: ${config.content_density}`,
    `Review：${config.review_mode}`,
    `${locale === "zh-CN" ? "后端" : "Backend"}: ${run?.backend ?? config.provider ?? "heuristic"}`,
    `${locale === "zh-CN" ? "模型" : "Models"}: ${locale === "zh-CN" ? "简单" : "Simple"} ${run?.simple_model ?? config.simple_model ?? (locale === "zh-CN" ? "未配置" : "Not configured")} / ${locale === "zh-CN" ? "复杂" : "Complex"} ${
      run?.complex_model ?? config.complex_model ?? (locale === "zh-CN" ? "未配置" : "Not configured")
    }`,
  ];
}

function buildRuntimeItems(
  locale: Locale,
  run?: RunSession | null,
): string[] {
  if (!run) {
    return [
      locale === "zh-CN"
        ? "运行开始后，这里将显示本次任务的关键信息与执行摘要。"
        : "Runtime state and execution summary will appear here after a run starts.",
    ];
  }

  const completedCount = run.stages.filter((stage) => stage.status === "completed").length;
  const currentStage =
    run.stages.find((stage) => stage.status === "running")?.name ??
    run.stages.find((stage) => stage.status === "failed")?.name ??
    run.stages.find((stage) => stage.status === "pending")?.name ??
    (locale === "zh-CN" ? "无" : "None");

  const items = [
    `${locale === "zh-CN" ? "状态" : "Status"}: ${run.status}`,
    `${locale === "zh-CN" ? "目标产物" : "Target Output"}: ${run.target_output ?? (locale === "zh-CN" ? "未配置" : "Not configured")}`,
    `${locale === "zh-CN" ? "已完成阶段" : "Completed Stages"}: ${completedCount}/${run.stages.length}`,
    `${locale === "zh-CN" ? "当前阶段" : "Current Stage"}: ${currentStage}`,
  ];

  if (run.last_error) {
    items.push(`${locale === "zh-CN" ? "最近错误" : "Last Error"}: ${run.last_error}`);
  }

  return items;
}

export function buildContextSections({
  locale = "zh-CN",
  draft,
  run,
}: {
  locale?: Locale;
  draft?: CourseDraft | null;
  run?: RunSession | null;
  reviewSummary?: ReviewSummary | null;
}): ContextSection[] {
  return [
    {
      title: locale === "zh-CN" ? "课程摘要" : "Course Summary",
      items: buildCourseItems(locale, draft),
    },
    {
      title: locale === "zh-CN" ? "模板摘要" : "Template Summary",
      items: buildTemplateItems(locale, draft, run),
    },
    {
      title: locale === "zh-CN" ? "运行摘要" : "Runtime Summary",
      items: buildRuntimeItems(locale, run),
    },
  ];
}
