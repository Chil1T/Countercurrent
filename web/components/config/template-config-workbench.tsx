"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { getCourseDraft } from "@/lib/api/course-drafts";
import { createRun } from "@/lib/api/runs";
import {
  getConfigWorkbenchCopy,
  getConfigWorkbenchLayout,
} from "@/lib/config-workbench-view";
import {
  DraftConfig,
  getGuiRuntimeConfig,
  GuiRuntimeConfig,
  HostedProviderSettings,
  listTemplates,
  ProviderName,
  saveCourseDraftConfig,
  saveGuiRuntimeConfig,
  TemplatePreset,
} from "@/lib/api/templates";

type ProviderFormState = {
  api_key: string;
  base_url: string;
  simple_model: string;
  complex_model: string;
  timeout_seconds: string;
};

type ProviderSettingsMap = {
  openai: ProviderFormState;
  openai_compatible: ProviderFormState;
  anthropic: ProviderFormState;
};

const fieldCardClass =
  "rounded-2xl border border-stone-200 bg-stone-50 px-4 py-4 text-sm text-stone-700";
const fieldLabelClass = "font-medium text-stone-700";
const helperTextClass = "mt-1 text-xs leading-6 text-stone-500";
const selectClass =
  "mt-3 w-full appearance-none rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-800 outline-none transition hover:border-stone-300 focus:border-stone-500";
const inputClass =
  "mt-3 w-full rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-800 outline-none transition hover:border-stone-300 focus:border-stone-500";

const configWorkbenchCopy = getConfigWorkbenchCopy();
const configWorkbenchLayout = getConfigWorkbenchLayout();

function emptyProviderFormState(): ProviderFormState {
  return {
    api_key: "",
    base_url: "",
    simple_model: "",
    complex_model: "",
    timeout_seconds: "",
  };
}

function emptyProviderSettingsMap(): ProviderSettingsMap {
  return {
    openai: emptyProviderFormState(),
    openai_compatible: emptyProviderFormState(),
    anthropic: emptyProviderFormState(),
  };
}

function providerStateFromApi(settings: HostedProviderSettings): ProviderFormState {
  return {
    api_key: settings.api_key ?? "",
    base_url: settings.base_url ?? "",
    simple_model: settings.simple_model ?? "",
    complex_model: settings.complex_model ?? "",
    timeout_seconds: settings.timeout_seconds == null ? "" : String(settings.timeout_seconds),
  };
}

function providerStateToApi(settings: ProviderFormState): HostedProviderSettings {
  const timeout = settings.timeout_seconds.trim();
  return {
    api_key: settings.api_key.trim() || null,
    base_url: settings.base_url.trim() || null,
    simple_model: settings.simple_model.trim() || null,
    complex_model: settings.complex_model.trim() || null,
    timeout_seconds: timeout ? Number(timeout) : null,
  };
}

function providerLabel(provider: ProviderName): string {
  return {
    heuristic: "heuristic",
    openai: "OpenAI",
    openai_compatible: "OpenAI-compatible",
    anthropic: "Anthropic",
  }[provider];
}

export function TemplateConfigWorkbench() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const draftId = searchParams.get("draftId");

  const [templates, setTemplates] = useState<TemplatePreset[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [contentDensity, setContentDensity] = useState("balanced");
  const [reviewMode, setReviewMode] = useState("light");
  const [reviewEnabled, setReviewEnabled] = useState(false);
  const [exportPackage, setExportPackage] = useState(true);
  const [savedConfig, setSavedConfig] = useState<DraftConfig | null>(null);
  const [isStartingRun, setIsStartingRun] = useState(false);
  const [isStartingGlobalRun, setIsStartingGlobalRun] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingRuntimeDefaults, setIsSavingRuntimeDefaults] = useState(false);
  const [defaultProvider, setDefaultProvider] = useState<ProviderName>("heuristic");
  const [providerSettings, setProviderSettings] = useState<ProviderSettingsMap>(emptyProviderSettingsMap());
  const [courseProvider, setCourseProvider] = useState<string>("");
  const [courseBaseUrl, setCourseBaseUrl] = useState("");
  const [courseSimpleModel, setCourseSimpleModel] = useState("");
  const [courseComplexModel, setCourseComplexModel] = useState("");
  const [courseTimeoutSeconds, setCourseTimeoutSeconds] = useState("");
  const [runReviewOverride, setRunReviewOverride] = useState<"default" | "enabled" | "disabled">("default");

  useEffect(() => {
    let cancelled = false;

    async function loadPageDependencies() {
      setIsLoading(true);
      setError(null);
      try {
        const [nextTemplates, runtimeConfig] = await Promise.all([
          listTemplates(),
          getGuiRuntimeConfig(),
        ]);
        if (cancelled) {
          return;
        }
        setTemplates(nextTemplates);
        setSelectedTemplateId((current) => current || nextTemplates[0]?.id || "");
        setDefaultProvider(runtimeConfig.default_provider);
        setProviderSettings({
          openai: providerStateFromApi(runtimeConfig.providers.openai),
          openai_compatible: providerStateFromApi(runtimeConfig.providers.openai_compatible),
          anthropic: providerStateFromApi(runtimeConfig.providers.anthropic),
        });
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadPageDependencies();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadDraft() {
      if (!draftId) {
        if (!cancelled) {
          setSavedConfig(null);
          setCourseProvider("");
          setCourseBaseUrl("");
          setCourseSimpleModel("");
          setCourseComplexModel("");
          setCourseTimeoutSeconds("");
          setReviewEnabled(false);
        }
        return;
      }

      try {
        const draft = await getCourseDraft(draftId);
        if (cancelled) {
          return;
        }

        if (draft.config) {
          setSavedConfig(draft.config);
          setSelectedTemplateId(draft.config.template.id);
          setContentDensity(draft.config.content_density);
          setReviewMode(draft.config.review_mode);
          setReviewEnabled(draft.config.review_enabled);
          setExportPackage(draft.config.export_package);
          setCourseProvider(draft.config.provider ?? "");
          setCourseBaseUrl(draft.config.base_url ?? "");
          setCourseSimpleModel(draft.config.simple_model ?? "");
          setCourseComplexModel(draft.config.complex_model ?? "");
          setCourseTimeoutSeconds(
            draft.config.timeout_seconds == null ? "" : String(draft.config.timeout_seconds),
          );
        } else {
          setSavedConfig(null);
          setCourseProvider("");
          setCourseBaseUrl("");
          setCourseSimpleModel("");
          setCourseComplexModel("");
          setCourseTimeoutSeconds("");
          setReviewEnabled(false);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      }
    }

    void loadDraft();

    return () => {
      cancelled = true;
    };
  }, [draftId]);

  const selectedTemplate = useMemo(
    () => templates.find((item) => item.id === selectedTemplateId) ?? null,
    [selectedTemplateId, templates],
  );
  const activeDefaultProviderSettings =
    defaultProvider === "heuristic" ? null : providerSettings[defaultProvider];

  const effectiveProvider = (courseProvider || defaultProvider) as ProviderName;
  const effectiveRuntimeDefaults =
    effectiveProvider === "heuristic" ? null : providerSettings[effectiveProvider];

  function updateProviderSettings(
    provider: keyof ProviderSettingsMap,
    field: keyof ProviderFormState,
    value: string,
  ) {
    setProviderSettings((current) => ({
      ...current,
      [provider]: {
        ...current[provider],
        [field]: value,
      },
    }));
  }

  async function handleSaveRuntimeDefaults() {
    setIsSavingRuntimeDefaults(true);
    setError(null);
    try {
      const payload: GuiRuntimeConfig = {
        default_provider: defaultProvider,
        providers: {
          openai: providerStateToApi(providerSettings.openai),
          openai_compatible: providerStateToApi(providerSettings.openai_compatible),
          anthropic: providerStateToApi(providerSettings.anthropic),
        },
      };
      const saved = await saveGuiRuntimeConfig(payload);
      setDefaultProvider(saved.default_provider);
      setProviderSettings({
        openai: providerStateFromApi(saved.providers.openai),
        openai_compatible: providerStateFromApi(saved.providers.openai_compatible),
        anthropic: providerStateFromApi(saved.providers.anthropic),
      });
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unknown error");
    } finally {
      setIsSavingRuntimeDefaults(false);
    }
  }

  async function handleSave() {
    if (!draftId || !selectedTemplateId) {
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      const config = await saveCourseDraftConfig(draftId, {
        template_id: selectedTemplateId,
        content_density: contentDensity,
        review_mode: reviewMode,
        review_enabled: reviewEnabled,
        export_package: exportPackage,
        provider: (courseProvider || null) as ProviderName | null,
        base_url: courseBaseUrl.trim() || null,
        simple_model: courseSimpleModel.trim() || null,
        complex_model: courseComplexModel.trim() || null,
        timeout_seconds: courseTimeoutSeconds.trim() ? Number(courseTimeoutSeconds) : null,
      });
      setSavedConfig(config);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unknown error");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleStartRun() {
    if (!draftId) {
      return;
    }

    setIsStartingRun(true);
    setError(null);
    try {
      const reviewOverride =
        runReviewOverride === "default" ? undefined : runReviewOverride === "enabled";
      const run = await createRun(draftId, { review_enabled: reviewOverride, run_kind: "chapter" });
      router.push(
        `/runs/${run.id}?draftId=${encodeURIComponent(run.draft_id)}&courseId=${encodeURIComponent(run.course_id)}`,
      );
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Unknown error");
    } finally {
      setIsStartingRun(false);
    }
  }

  async function handleStartGlobalRun() {
    if (!draftId) {
      return;
    }

    setIsStartingGlobalRun(true);
    setError(null);
    try {
      const run = await createRun(draftId, { run_kind: "global" });
      router.push(
        `/runs/${run.id}?draftId=${encodeURIComponent(run.draft_id)}&courseId=${encodeURIComponent(run.course_id)}`,
      );
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Unknown error");
    } finally {
      setIsStartingGlobalRun(false);
    }
  }

  return (
    <section className="grid gap-5 xl:grid-cols-[220px_minmax(0,1fr)_280px]">
      <div className="xl:self-start xl:sticky xl:top-24">
        <div className="min-w-0 rounded-[28px] border border-stone-200 bg-stone-50 p-5">
          <h3 className="text-lg font-semibold">模板列表</h3>
          <div className="mt-4 space-y-3">
            {isLoading ? (
              <div className="rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-500">
                正在加载模板...
              </div>
            ) : null}
            {templates.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelectedTemplateId(item.id)}
                className={`block w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                  item.id === selectedTemplateId
                    ? "border-stone-900 bg-stone-900 text-white"
                    : "border-stone-200 bg-white text-stone-700 hover:bg-stone-100"
                }`}
              >
                <div className="font-medium">{item.name}</div>
                <div className="mt-1 text-xs leading-6 opacity-80">{item.description}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="min-w-0 space-y-5">
        <div className="rounded-[28px] border border-stone-200 bg-white p-5 xl:p-6">
          <h3 className="text-xl font-semibold">参数编辑器</h3>
          <div className={configWorkbenchLayout.primaryFieldGridClass}>
            <label className={configWorkbenchLayout.primaryFieldCardClass}>
              <div className={fieldLabelClass}>内容密度</div>
              <div className={helperTextClass}>控制单章内容的展开程度，越高越详细。</div>
              <select
                value={contentDensity}
                onChange={(event) => setContentDensity(event.target.value)}
                className={selectClass}
              >
                <option value="light">light</option>
                <option value="balanced">balanced</option>
                <option value="dense">dense</option>
              </select>
            </label>

            <label className={configWorkbenchLayout.primaryFieldCardClass}>
              <div className={fieldLabelClass}>{configWorkbenchCopy.reviewModeLabel}</div>
              <div className={helperTextClass}>{configWorkbenchCopy.reviewModeHelpText}</div>
              <select
                value={reviewMode}
                onChange={(event) => setReviewMode(event.target.value)}
                className={selectClass}
              >
                <option value="light">light</option>
                <option value="standard">standard</option>
                <option value="strict">strict</option>
              </select>
            </label>

            <label className={`${fieldCardClass} md:col-span-2`}>
              <div className="flex items-center justify-between">
                <span className={fieldLabelClass}>{configWorkbenchCopy.reviewEnabledLabel}</span>
                <input
                  checked={reviewEnabled}
                  onChange={(event) => setReviewEnabled(event.target.checked)}
                  type="checkbox"
                  className="h-4 w-4"
                />
              </div>
              <div className={helperTextClass}>{configWorkbenchCopy.reviewEnabledHelpText}</div>
            </label>

            <label className={`${fieldCardClass} md:col-span-2`}>
              <div className="flex items-center justify-between">
                <span className={fieldLabelClass}>导出 ZIP</span>
                <input
                  checked={exportPackage}
                  onChange={(event) => setExportPackage(event.target.checked)}
                  type="checkbox"
                  className="h-4 w-4"
                />
              </div>
              <div className={helperTextClass}>决定结果页是否提供一键打包下载。</div>
            </label>
          </div>
        </div>

        <details
          className="rounded-[28px] border border-stone-200 bg-white p-5 xl:p-6"
          open={configWorkbenchLayout.runtimeDefaultsDefaultOpen}
        >
          <summary className="cursor-pointer list-none text-xl font-semibold text-stone-900">
            {configWorkbenchCopy.runtimeDefaultsTitle}
          </summary>
          <div className="mt-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <p className="text-sm leading-7 text-stone-500">
                {configWorkbenchCopy.runtimeDefaultsHelpText}
              </p>
              <button
                type="button"
                onClick={() => void handleSaveRuntimeDefaults()}
                disabled={isSavingRuntimeDefaults}
                className="rounded-full border border-stone-300 px-5 py-3 text-sm font-medium text-stone-700 transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
              >
                {isSavingRuntimeDefaults ? "保存中..." : "保存默认值"}
              </button>
            </div>

            <div className={`mt-5 ${fieldCardClass}`}>
              <div className={fieldLabelClass}>默认 provider</div>
              <div className={helperTextClass}>选择新课程默认使用哪类后端。后面的表单会随此选项切换。</div>
              <select
                value={defaultProvider}
                onChange={(event) => setDefaultProvider(event.target.value as ProviderName)}
                className={selectClass}
              >
                <option value="heuristic">heuristic</option>
                <option value="openai">OpenAI</option>
                <option value="openai_compatible">OpenAI-compatible</option>
                <option value="anthropic">Anthropic</option>
              </select>
            </div>

            <div className="mt-5 space-y-4">
              {defaultProvider === "heuristic" ? (
                <div className={fieldCardClass}>
                  <div className={fieldLabelClass}>heuristic 默认配置</div>
                  <div className="mt-3 rounded-2xl border border-dashed border-stone-300 bg-white px-4 py-4 text-sm leading-7 text-stone-600">
                    heuristic 使用本地启发式流程，不需要填写 API key、模型或 base URL。
                  </div>
                </div>
              ) : (
                <div className={fieldCardClass}>
                  <div className={fieldLabelClass}>{providerLabel(defaultProvider)} 默认配置</div>
                  <div className={helperTextClass}>
                    这里只显示当前默认 provider 的连接信息，切换 provider 会切换到对应卡片。
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <label className="text-sm text-stone-700">
                      <div className={fieldLabelClass}>API key</div>
                      <div className={helperTextClass}>用于调用所选服务商的密钥。</div>
                      <input
                        value={activeDefaultProviderSettings?.api_key ?? ""}
                        onChange={(event) => updateProviderSettings(defaultProvider, "api_key", event.target.value)}
                        placeholder="粘贴服务商提供的 API key"
                        className={inputClass}
                      />
                    </label>
                    <label className="text-sm text-stone-700">
                      <div className={fieldLabelClass}>Base URL</div>
                      <div className={helperTextClass}>只有自定义网关时才需要填写，官方地址可留空。</div>
                      <input
                        value={activeDefaultProviderSettings?.base_url ?? ""}
                        onChange={(event) => updateProviderSettings(defaultProvider, "base_url", event.target.value)}
                        placeholder={
                          defaultProvider === "openai_compatible"
                            ? "例如：https://openrouter.ai/api/v1/chat/completions"
                            : "留空使用官方默认地址"
                        }
                        className={inputClass}
                      />
                    </label>
                    <label className="text-sm text-stone-700">
                      <div className={fieldLabelClass}>简单任务模型</div>
                      <div className={helperTextClass}>适合术语、摘要等轻量步骤。</div>
                      <input
                        value={activeDefaultProviderSettings?.simple_model ?? ""}
                        onChange={(event) => updateProviderSettings(defaultProvider, "simple_model", event.target.value)}
                        placeholder="例如：gpt-4.1-mini"
                        className={inputClass}
                      />
                    </label>
                    <label className="text-sm text-stone-700">
                      <div className={fieldLabelClass}>复杂任务模型</div>
                      <div className={helperTextClass}>适合写作、整合和推理更重的步骤。</div>
                      <input
                        value={activeDefaultProviderSettings?.complex_model ?? ""}
                        onChange={(event) => updateProviderSettings(defaultProvider, "complex_model", event.target.value)}
                        placeholder="例如：gpt-5.4"
                        className={inputClass}
                      />
                    </label>
                    <label className="text-sm text-stone-700 md:col-span-2">
                      <div className={fieldLabelClass}>请求超时（秒）</div>
                      <div className={helperTextClass}>控制单次模型请求最多等待多久，不是整次运行总时长。</div>
                      <input
                        value={activeDefaultProviderSettings?.timeout_seconds ?? ""}
                        onChange={(event) => updateProviderSettings(defaultProvider, "timeout_seconds", event.target.value)}
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

        <div className="rounded-[28px] border border-stone-200 bg-white p-5 xl:p-6">
          <div className="mb-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
            <label className={fieldCardClass}>
              <div className={fieldLabelClass}>本次运行 review 覆盖</div>
              <div className={helperTextClass}>只影响这一次章节运行；留在“跟随课程默认”时，会使用上面保存的课程设置。</div>
              <select
                value={runReviewOverride}
                onChange={(event) => setRunReviewOverride(event.target.value as "default" | "enabled" | "disabled")}
                className={selectClass}
              >
                <option value="default">跟随课程默认</option>
                <option value="enabled">本次开启 review</option>
                <option value="disabled">本次关闭 review</option>
              </select>
            </label>
            <div className={fieldCardClass}>
              <div className={fieldLabelClass}>全局汇总</div>
              <div className={helperTextClass}>章节主流程默认不再重跑 `global/*`，需要时手动触发。</div>
              <button
                type="button"
                onClick={() => void handleStartGlobalRun()}
                disabled={!draftId || isStartingGlobalRun}
                className="mt-3 w-full rounded-full border border-stone-300 px-4 py-3 text-sm font-medium text-stone-700 transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
              >
                {isStartingGlobalRun ? "更新中..." : "更新全局汇总"}
              </button>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={!draftId || isSaving || !selectedTemplateId}
              className="rounded-full bg-stone-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-stone-700 disabled:cursor-not-allowed disabled:bg-stone-400"
            >
              {isSaving ? "保存中..." : "保存模板配置"}
            </button>
            <span className="text-sm text-stone-600">
              {draftId ? `当前草稿：${draftId}` : "请先在输入页生成草稿"}
            </span>
            <button
              type="button"
              onClick={() => void handleStartRun()}
              disabled={!savedConfig || isStartingRun || isStartingGlobalRun}
              className="rounded-full border border-stone-300 px-5 py-3 text-sm font-medium text-stone-700 transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
            >
              {isStartingRun ? "启动中..." : "启动 / 继续运行"}
            </button>
          </div>
          <p className="mt-3 text-sm leading-7 text-stone-500">
            章节主流程默认只更新本章产物并复用有效 checkpoint；`global/*` 需要单独手动触发。如果你需要强制全量重跑，请先在运行页执行 `Clean`。
          </p>

          {error ? (
            <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
        </div>
      </div>

      <div className="2xl:self-start 2xl:sticky 2xl:top-24 xl:self-start xl:sticky xl:top-24">
        <div className="min-w-0 rounded-[28px] border border-stone-200 bg-[#15120f] p-5 text-stone-100">
          <h3 className="text-lg font-semibold">产物摘要</h3>
          <div className="mt-3 space-y-4 text-sm leading-7 text-stone-300">
            <div>
              <div className="font-medium text-stone-100">当前模板</div>
              <div>{selectedTemplate?.name ?? "未选择"}</div>
            </div>
            <div>
              <div className="font-medium text-stone-100">预期输出</div>
              <ul className="mt-1 list-disc pl-5">
                {(selectedTemplate?.expected_outputs ?? []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="font-medium text-stone-100">有效运行后端</div>
              <div>{providerLabel(effectiveProvider)}</div>
            </div>
            <div>
              <div className="font-medium text-stone-100">有效模型路由</div>
              <div className="break-words">
                simple: {courseSimpleModel || effectiveRuntimeDefaults?.simple_model || "未设置"}
              </div>
              <div className="break-words">
                complex: {courseComplexModel || effectiveRuntimeDefaults?.complex_model || "未设置"}
              </div>
            </div>
            <div>
              <div className="font-medium text-stone-100">已保存配置</div>
              <div>
                {savedConfig
                  ? `${savedConfig.template.name} / ${savedConfig.content_density} / review ${savedConfig.review_enabled ? "on" : "off"}`
                  : "尚未保存"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
