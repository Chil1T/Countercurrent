"use client";

import { DraftConfig, ProviderName, TemplatePreset } from "@/lib/api/templates";
import { SurfaceCard } from "@/components/stitch-v2/surface-card";
import { StatusChip } from "@/components/stitch-v2/status-chip";

export type ProviderFormState = {
  api_key: string;
  base_url: string;
  simple_model: string;
  complex_model: string;
  timeout_seconds: string;
};

const selectClass =
  "mt-3 w-full appearance-none rounded-[1.25rem] border border-[var(--stitch-shell-border)] bg-white/92 px-4 py-3 text-sm text-stone-800 outline-none transition hover:border-[var(--stitch-shell-border-strong)] focus:border-[var(--stitch-shell-primary)]";
const inputClass =
  "mt-3 w-full rounded-[1.25rem] border border-[var(--stitch-shell-border)] bg-white/92 px-4 py-3 text-sm text-stone-800 outline-none transition hover:border-[var(--stitch-shell-border-strong)] focus:border-[var(--stitch-shell-primary)]";
const softFieldClass =
  "rounded-[1.5rem] border border-[var(--stitch-shell-border)] bg-[var(--stitch-shell-panel-soft)] px-5 py-5 text-sm text-stone-700";

export function ConfigV2Sections({
  isLoading,
  templates,
  selectedTemplateId,
  selectedTemplate,
  contentDensity,
  reviewMode,
  reviewEnabled,
  exportPackage,
  defaultProvider,
  activeDefaultProviderSettings,
  isSavingRuntimeDefaults,
  runtimeDefaultsTitle,
  runtimeDefaultsHelpText,
  runtimeDefaultsDefaultOpen,
  runReviewOverride,
  draftId,
  isSaving,
  isStartingRun,
  isStartingGlobalRun,
  savedConfig,
  error,
  effectiveProviderLabel,
  effectiveSimpleModel,
  effectiveComplexModel,
  onSelectTemplate,
  onContentDensityChange,
  onReviewModeChange,
  onReviewEnabledChange,
  onExportPackageChange,
  onDefaultProviderChange,
  onProviderFieldChange,
  onSaveRuntimeDefaults,
  onRunReviewOverrideChange,
  onSave,
  onStartRun,
  onStartGlobalRun,
}: {
  isLoading: boolean;
  templates: TemplatePreset[];
  selectedTemplateId: string;
  selectedTemplate: TemplatePreset | null;
  contentDensity: string;
  reviewMode: string;
  reviewEnabled: boolean;
  exportPackage: boolean;
  defaultProvider: ProviderName;
  activeDefaultProviderSettings: ProviderFormState | null;
  isSavingRuntimeDefaults: boolean;
  runtimeDefaultsTitle: string;
  runtimeDefaultsHelpText: string;
  runtimeDefaultsDefaultOpen: boolean;
  runReviewOverride: "default" | "enabled" | "disabled";
  draftId: string | null;
  isSaving: boolean;
  isStartingRun: boolean;
  isStartingGlobalRun: boolean;
  savedConfig: DraftConfig | null;
  error: string | null;
  effectiveProviderLabel: string;
  effectiveSimpleModel: string;
  effectiveComplexModel: string;
  onSelectTemplate: (templateId: string) => void;
  onContentDensityChange: (value: string) => void;
  onReviewModeChange: (value: string) => void;
  onReviewEnabledChange: (value: boolean) => void;
  onExportPackageChange: (value: boolean) => void;
  onDefaultProviderChange: (value: ProviderName) => void;
  onProviderFieldChange: (field: keyof ProviderFormState, value: string) => void;
  onSaveRuntimeDefaults: () => void;
  onRunReviewOverrideChange: (value: "default" | "enabled" | "disabled") => void;
  onSave: () => void;
  onStartRun: () => void;
  onStartGlobalRun: () => void;
}) {
  return (
    <section className="grid gap-6 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
      <div className="xl:self-start xl:sticky xl:top-24">
        <SurfaceCard className="p-5 md:p-6">
          <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-[var(--stitch-shell-primary-strong)]">
            Templates
          </p>
          <h3 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-stone-900">
            预设模板
          </h3>
          <div className="mt-5 space-y-3">
            {isLoading ? (
              <div className="rounded-[1.25rem] border border-[var(--stitch-shell-border)] bg-white/90 px-4 py-3 text-sm text-stone-500">
                正在加载模板...
              </div>
            ) : null}
            {templates.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTemplate(item.id)}
                className={`block w-full rounded-[1.4rem] border px-4 py-4 text-left transition ${
                  item.id === selectedTemplateId
                    ? "border-[var(--stitch-shell-primary)] bg-[var(--stitch-shell-primary)] text-white shadow-[var(--stitch-shell-shadow-soft)]"
                    : "border-[var(--stitch-shell-border)] bg-white/92 text-stone-700 hover:bg-[var(--stitch-shell-panel-soft)]"
                }`}
              >
                <div className="text-sm font-semibold">{item.name}</div>
                <div className="mt-2 text-xs leading-6 opacity-80">{item.description}</div>
              </button>
            ))}
          </div>
        </SurfaceCard>
      </div>

      <div className="min-w-0 space-y-6">
        <SurfaceCard className="overflow-hidden p-6 md:p-7 xl:p-8">
          <div className="grid gap-8 xl:grid-cols-[1.12fr_0.88fr]">
            <div>
              <p className="font-stitch-label text-[11px] uppercase tracking-[0.34em] text-[var(--stitch-shell-primary-strong)]">
                Logic Parameters
              </p>
              <h3 className="font-stitch-headline mt-4 text-4xl font-black tracking-[-0.05em] text-stone-900 md:text-5xl">
                ReCurr Configuration
              </h3>
              <p className="mt-5 max-w-2xl text-sm leading-8 text-stone-600 md:text-base">
                定义模板、Review、AI 服务配置与运行动作，让课程级生产路径保持清晰且可重复。
              </p>
            </div>

            <div className="rounded-[1.75rem] bg-[var(--stitch-shell-rail)] p-5 text-stone-100 shadow-[var(--stitch-shell-shadow-strong)]">
              <p className="font-stitch-label text-[11px] uppercase tracking-[0.3em] text-white/55">
                Focus Areas
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <StatusChip label="Template Logic" tone="accent" />
                <StatusChip label="AI 服务配置" tone="default" />
                <StatusChip label="Run Controls" tone="default" />
              </div>
              <p className="mt-5 text-sm leading-7 text-white/72">
                V2 只重做信息层级和视觉壳层，不恢复已经从产品面移除的高级控制。
              </p>
            </div>
          </div>
        </SurfaceCard>

        <SurfaceCard className="p-6 md:p-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-[var(--stitch-shell-primary-strong)]">
                Logic Parameters
              </p>
              <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-stone-900">
                模板与 Review 参数
              </h4>
            </div>
            {selectedTemplate ? <StatusChip label={selectedTemplate.name} tone="accent" /> : null}
          </div>

          <div className="mt-6 grid gap-5 md:grid-cols-2">
            <label className={softFieldClass}>
              <div className="font-semibold text-stone-800">内容密度</div>
              <div className="mt-2 text-xs leading-6 text-stone-500">控制单章内容的展开程度，越高越详细。</div>
              <select
                value={contentDensity}
                onChange={(event) => onContentDensityChange(event.target.value)}
                className={selectClass}
              >
                <option value="light">light</option>
                <option value="balanced">balanced</option>
                <option value="dense">dense</option>
              </select>
            </label>

            <label className={softFieldClass}>
              <div className="font-semibold text-stone-800">Review 策略</div>
              <div className="mt-2 text-xs leading-6 text-stone-500">只有启用 Review 时才生效，控制检查的严格程度。</div>
              <select
                value={reviewMode}
                onChange={(event) => onReviewModeChange(event.target.value)}
                className={selectClass}
              >
                <option value="light">light</option>
                <option value="standard">standard</option>
                <option value="strict">strict</option>
              </select>
            </label>

            <label className={`${softFieldClass} md:col-span-2`}>
              <div className="flex items-center justify-between gap-4">
                <span className="font-semibold text-stone-800">启用 Review</span>
                <input
                  checked={reviewEnabled}
                  onChange={(event) => onReviewEnabledChange(event.target.checked)}
                  type="checkbox"
                  className="h-4 w-4"
                />
              </div>
              <div className="mt-2 text-xs leading-6 text-stone-500">
                开启后，系统会在生成过程中增加 Review 环节，以帮助提升结果质量。默认关闭。
              </div>
            </label>

            <label className={`${softFieldClass} md:col-span-2`}>
              <div className="flex items-center justify-between gap-4">
                <span className="font-semibold text-stone-800">导出 ZIP</span>
                <input
                  checked={exportPackage}
                  onChange={(event) => onExportPackageChange(event.target.checked)}
                  type="checkbox"
                  className="h-4 w-4"
                />
              </div>
              <div className="mt-2 text-xs leading-6 text-stone-500">
                决定结果页是否提供一键打包下载。
              </div>
            </label>
          </div>
        </SurfaceCard>

        <details
          className="rounded-[2rem] border border-[var(--stitch-shell-border)] bg-white/94 p-6 md:p-7"
          open={runtimeDefaultsDefaultOpen}
        >
          <summary className="cursor-pointer list-none">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-[var(--stitch-shell-primary-strong)]">
                  AI Service
                </p>
                <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-stone-900">
                  {runtimeDefaultsTitle}
                </h4>
              </div>
              <StatusChip label={defaultProvider === "heuristic" ? "heuristic" : defaultProvider} tone="default" />
            </div>
          </summary>

          <div className="mt-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <p className="text-sm leading-7 text-stone-500">{runtimeDefaultsHelpText}</p>
              <button
                type="button"
                onClick={onSaveRuntimeDefaults}
                disabled={isSavingRuntimeDefaults}
                className="rounded-full border border-[var(--stitch-shell-border)] px-5 py-3 text-sm font-semibold text-stone-700 transition hover:bg-[var(--stitch-shell-panel-soft)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSavingRuntimeDefaults ? "保存中..." : "保存默认值"}
              </button>
            </div>

            <div className="mt-5 grid gap-5">
              <label className={softFieldClass}>
                <div className="font-semibold text-stone-800">默认 provider</div>
                <div className="mt-2 text-xs leading-6 text-stone-500">
                  选择新课程默认使用哪类后端。后面的表单会随此选项切换。
                </div>
                <select
                  value={defaultProvider}
                  onChange={(event) => onDefaultProviderChange(event.target.value as ProviderName)}
                  className={selectClass}
                >
                  <option value="heuristic">heuristic</option>
                  <option value="openai">OpenAI</option>
                  <option value="openai_compatible">OpenAI-compatible</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </label>

              {defaultProvider === "heuristic" ? (
                <div className={softFieldClass}>
                  <div className="font-semibold text-stone-800">heuristic 默认配置</div>
                  <div className="mt-3 rounded-[1.25rem] border border-dashed border-[var(--stitch-shell-border)] bg-white/92 px-4 py-4 text-sm leading-7 text-stone-600">
                    heuristic 使用本地启发式流程，不需要填写 API key、模型或 base URL。
                  </div>
                </div>
              ) : (
                <div className={softFieldClass}>
                  <div className="font-semibold text-stone-800">连接与模型配置</div>
                  <div className="mt-2 text-xs leading-6 text-stone-500">
                    这里只显示当前默认 provider 的连接信息，切换 provider 会切换到对应卡片。
                  </div>
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <label className="text-sm text-stone-700">
                      <div className="font-semibold text-stone-800">API key</div>
                      <div className="mt-2 text-xs leading-6 text-stone-500">用于调用所选服务商的密钥。</div>
                      <input
                        value={activeDefaultProviderSettings?.api_key ?? ""}
                        onChange={(event) => onProviderFieldChange("api_key", event.target.value)}
                        placeholder="粘贴服务商提供的 API key"
                        className={inputClass}
                      />
                    </label>
                    <label className="text-sm text-stone-700">
                      <div className="font-semibold text-stone-800">Base URL</div>
                      <div className="mt-2 text-xs leading-6 text-stone-500">只有自定义网关时才需要填写，官方地址可留空。</div>
                      <input
                        value={activeDefaultProviderSettings?.base_url ?? ""}
                        onChange={(event) => onProviderFieldChange("base_url", event.target.value)}
                        placeholder={
                          defaultProvider === "openai_compatible"
                            ? "例如：https://openrouter.ai/api/v1/chat/completions"
                            : "留空使用官方默认地址"
                        }
                        className={inputClass}
                      />
                    </label>
                    <label className="text-sm text-stone-700">
                      <div className="font-semibold text-stone-800">简单任务模型</div>
                      <div className="mt-2 text-xs leading-6 text-stone-500">适合术语、摘要等轻量步骤。</div>
                      <input
                        value={activeDefaultProviderSettings?.simple_model ?? ""}
                        onChange={(event) => onProviderFieldChange("simple_model", event.target.value)}
                        placeholder="例如：gpt-4.1-mini"
                        className={inputClass}
                      />
                    </label>
                    <label className="text-sm text-stone-700">
                      <div className="font-semibold text-stone-800">复杂任务模型</div>
                      <div className="mt-2 text-xs leading-6 text-stone-500">适合写作、整合和推理更重的步骤。</div>
                      <input
                        value={activeDefaultProviderSettings?.complex_model ?? ""}
                        onChange={(event) => onProviderFieldChange("complex_model", event.target.value)}
                        placeholder="例如：gpt-5.4"
                        className={inputClass}
                      />
                    </label>
                    <label className="text-sm text-stone-700 md:col-span-2">
                      <div className="font-semibold text-stone-800">请求超时（秒）</div>
                      <div className="mt-2 text-xs leading-6 text-stone-500">控制单次模型请求最多等待多久，不是整次运行总时长。</div>
                      <input
                        value={activeDefaultProviderSettings?.timeout_seconds ?? ""}
                        onChange={(event) => onProviderFieldChange("timeout_seconds", event.target.value)}
                        placeholder="例如：180"
                        className={inputClass}
                      />
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>
        </details>

        <SurfaceCard className="p-6 md:p-7">
          <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_220px]">
            <label className={softFieldClass}>
              <div className="font-semibold text-stone-800">本次运行 review 覆盖</div>
              <div className="mt-2 text-xs leading-6 text-stone-500">
                只影响这一次章节运行；留在“跟随课程默认”时，会使用上面保存的课程设置。
              </div>
              <select
                value={runReviewOverride}
                onChange={(event) => onRunReviewOverrideChange(event.target.value as "default" | "enabled" | "disabled")}
                className={selectClass}
              >
                <option value="default">跟随课程默认</option>
                <option value="enabled">本次开启 review</option>
                <option value="disabled">本次关闭 review</option>
              </select>
            </label>

            <div className={softFieldClass}>
              <div className="font-semibold text-stone-800">全局汇总</div>
              <div className="mt-2 text-xs leading-6 text-stone-500">
                章节主流程默认不再重跑 `global/*`，需要时手动触发。
              </div>
              <button
                type="button"
                onClick={onStartGlobalRun}
                disabled={!draftId || isStartingGlobalRun}
                className="mt-4 w-full rounded-full border border-[var(--stitch-shell-border)] px-4 py-3 text-sm font-semibold text-stone-700 transition hover:bg-[var(--stitch-shell-panel-soft)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isStartingGlobalRun ? "更新中..." : "更新全局汇总"}
              </button>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={onSave}
              disabled={!draftId || isSaving || !selectedTemplateId}
              className="rounded-full bg-[var(--stitch-shell-primary)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--stitch-shell-primary-strong)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSaving ? "保存中..." : "保存模板配置"}
            </button>
            <span className="text-sm text-stone-600">
              {draftId ? `当前草稿：${draftId}` : "请先在输入页生成草稿"}
            </span>
            <button
              type="button"
              onClick={onStartRun}
              disabled={!savedConfig || isStartingRun || isStartingGlobalRun}
              className="rounded-full border border-[var(--stitch-shell-border)] px-5 py-3 text-sm font-semibold text-stone-700 transition hover:bg-[var(--stitch-shell-panel-soft)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isStartingRun ? "启动中..." : "启动 / 继续运行"}
            </button>
          </div>

          <p className="mt-4 text-sm leading-7 text-stone-500">
            章节主流程默认只更新本章产物并复用有效 checkpoint；`global/*` 需要单独手动触发。如果你需要强制全量重跑，请先在运行页执行 `Clean`。
          </p>

          {error ? (
            <div className="mt-4 rounded-[1.5rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
        </SurfaceCard>
      </div>

      <div className="xl:self-start xl:sticky xl:top-24">
        <SurfaceCard tone="rail" className="p-6 md:p-7">
          <p className="font-stitch-label text-[11px] uppercase tracking-[0.3em] text-white/55">
            Output Summary
          </p>
          <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-white">
            产物摘要
          </h4>
          <div className="mt-6 space-y-4 text-sm leading-7 text-white/76">
            <div>
              <div className="font-semibold text-white">当前模板</div>
              <div>{selectedTemplate?.name ?? "未选择"}</div>
            </div>
            <div>
              <div className="font-semibold text-white">预期输出</div>
              <ul className="mt-2 list-disc pl-5">
                {(selectedTemplate?.expected_outputs ?? []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="font-semibold text-white">有效运行后端</div>
              <div>{effectiveProviderLabel}</div>
            </div>
            <div>
              <div className="font-semibold text-white">有效模型路由</div>
              <div className="break-words">simple: {effectiveSimpleModel}</div>
              <div className="break-words">complex: {effectiveComplexModel}</div>
            </div>
            <div>
              <div className="font-semibold text-white">已保存配置</div>
              <div>
                {savedConfig
                  ? `${savedConfig.template.name} / ${savedConfig.content_density} / review ${savedConfig.review_enabled ? "on" : "off"}`
                  : "尚未保存"}
              </div>
            </div>
          </div>
        </SurfaceCard>
      </div>
    </section>
  );
}
