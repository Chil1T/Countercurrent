export type ConfigWorkbenchCopy = {
  reviewEnabledLabel: string;
  reviewEnabledHelpText: string;
  reviewModeLabel: string;
  reviewModeHelpText: string;
  advancedSettingsSummary: string;
  courseOverridesTitle: string;
  courseOverridesHelpText: string;
};

export type ConfigWorkbenchLayout = {
  primaryFieldGridClass: string;
  primaryFieldCardClass: string;
  courseOverridesDefaultOpen: boolean;
};

const configWorkbenchCopy: ConfigWorkbenchCopy = {
  reviewEnabledLabel: "启用 Review",
  reviewEnabledHelpText: "开启后，系统会在生成过程中增加 Review 环节，以帮助提升结果质量。默认关闭。",
  reviewModeLabel: "Review 策略",
  reviewModeHelpText: "只有启用 Review 时才生效，控制检查的严格程度。",
  advancedSettingsSummary: "高级设置",
  courseOverridesTitle: "课程级运行覆盖",
  courseOverridesHelpText: "留空则继承全局默认值。当前采用 `simple_model` / `complex_model` 两层路由。",
};

const configWorkbenchLayout: ConfigWorkbenchLayout = {
  primaryFieldGridClass: "mt-5 grid gap-4 md:grid-cols-2 items-stretch",
  primaryFieldCardClass: "rounded-2xl border border-stone-200 bg-stone-50 px-4 py-4 text-sm text-stone-700 h-full",
  courseOverridesDefaultOpen: false,
};

export function getConfigWorkbenchCopy(): ConfigWorkbenchCopy {
  return configWorkbenchCopy;
}

export function getConfigWorkbenchLayout(): ConfigWorkbenchLayout {
  return configWorkbenchLayout;
}
