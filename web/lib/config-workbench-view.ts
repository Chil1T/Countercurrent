import type { Locale } from "./locale";

export type ConfigWorkbenchCopy = {
  reviewEnabledLabel: string;
  reviewEnabledHelpText: string;
  reviewModeLabel: string;
  reviewModeHelpText: string;
  runtimeDefaultsTitle: string;
  runtimeDefaultsHelpText: string;
};

export type ConfigWorkbenchLayout = {
  primaryFieldGridClass: string;
  primaryFieldCardClass: string;
  runtimeDefaultsDefaultOpen: boolean;
};

const configWorkbenchCopy: Record<Locale, ConfigWorkbenchCopy> = {
  "zh-CN": {
    reviewEnabledLabel: "启用 Review",
    reviewEnabledHelpText: "开启后，系统会在生成过程中增加 Review 环节，以帮助提升结果质量。默认关闭。",
    reviewModeLabel: "Review 策略",
    reviewModeHelpText: "只有启用 Review 时才生效，控制检查的严格程度。",
    runtimeDefaultsTitle: "AI 服务配置",
    runtimeDefaultsHelpText: "保存到本机 GUI 配置文件。当前版本密钥以仓库外本地明文方式保存。",
  },
  en: {
    reviewEnabledLabel: "Enable Review",
    reviewEnabledHelpText: "Adds a review stage during generation to improve output quality. Disabled by default.",
    reviewModeLabel: "Review Strategy",
    reviewModeHelpText: "Only applies when review is enabled and controls checking strictness.",
    runtimeDefaultsTitle: "AI Service Configuration",
    runtimeDefaultsHelpText: "Saved to the local GUI config file. Keys are currently stored as local plaintext outside the repository.",
  },
};

const configWorkbenchLayout: ConfigWorkbenchLayout = {
  primaryFieldGridClass: "mt-5 grid gap-4 md:grid-cols-2 items-stretch",
  primaryFieldCardClass: "rounded-2xl border border-stone-200 bg-stone-50 px-4 py-4 text-sm text-stone-700 h-full",
  runtimeDefaultsDefaultOpen: false,
};

export function getConfigWorkbenchCopy(locale: Locale = "zh-CN"): ConfigWorkbenchCopy {
  return configWorkbenchCopy[locale];
}

export function getConfigWorkbenchLayout(): ConfigWorkbenchLayout {
  return configWorkbenchLayout;
}
