"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { StitchV4ContextRail } from "@/components/stitch-v4/context-rail";
import { StitchV4RightRail, StitchV4TopNav } from "@/components/stitch-v4/chrome";
import { StitchV4MaterialSymbol } from "@/components/stitch-v4/material-symbol";
import { getCourseDraft } from "@/lib/api/course-drafts";
import { createRun } from "@/lib/api/runs";
import {
  getGuiRuntimeConfig,
  listTemplates,
  saveCourseDraftConfig,
  saveGuiRuntimeConfig,
  type DraftConfig,
  type GuiRuntimeConfig,
  type HostedProviderSettings,
  type ProviderName,
  type TemplatePreset,
} from "@/lib/api/templates";
import { useLocale } from "@/lib/locale";
import { getConfigWorkbenchCopy } from "@/lib/config-workbench-view";
import type { ProductContext } from "@/lib/product-nav";

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

function emptyProviderFormState(): ProviderFormState {
  return {
    api_key: "",
    base_url: "",
    simple_model: "",
    complex_model: "",
    timeout_seconds: "",
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
  return {
    api_key: settings.api_key.trim() || null,
    base_url: settings.base_url.trim() || null,
    simple_model: settings.simple_model.trim() || null,
    complex_model: settings.complex_model.trim() || null,
    timeout_seconds: settings.timeout_seconds.trim() ? Number(settings.timeout_seconds) : null,
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

export function StitchV4ConfigPage({
  initialDraftId,
  context,
}: {
  initialDraftId: string | null;
  context: ProductContext;
}) {
  const { messages, locale } = useLocale();
  const copy = getConfigWorkbenchCopy(locale);
  const router = useRouter();
  const [templates, setTemplates] = useState<TemplatePreset[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [contentDensity, setContentDensity] = useState("balanced");
  const [reviewMode, setReviewMode] = useState("light");
  const [reviewEnabled, setReviewEnabled] = useState(false);
  const [exportPackage, setExportPackage] = useState(true);
  const [draftConfig, setDraftConfig] = useState<DraftConfig | null>(null);
  const [draftCourseId, setDraftCourseId] = useState<string | null>(context.courseId ?? null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingRuntimeConfig, setIsSavingRuntimeConfig] = useState(false);
  const [isStartingRun, setIsStartingRun] = useState(false);
  const [isStartingGlobalRun, setIsStartingGlobalRun] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [defaultProvider, setDefaultProvider] = useState<ProviderName>("heuristic");
  const [providerSettings, setProviderSettings] = useState<ProviderSettingsMap>({
    openai: emptyProviderFormState(),
    openai_compatible: emptyProviderFormState(),
    anthropic: emptyProviderFormState(),
  });
  const [provider, setProvider] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [simpleModel, setSimpleModel] = useState("");
  const [complexModel, setComplexModel] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
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

        if (initialDraftId) {
          const draft = await getCourseDraft(initialDraftId);
          if (cancelled) {
            return;
          }
          setDraftCourseId(draft.course_id);
          if (draft.config) {
            setDraftConfig(draft.config);
            setSelectedTemplateId(draft.config.template.id);
            setContentDensity(draft.config.content_density);
            setReviewMode(draft.config.review_mode);
            setReviewEnabled(draft.config.review_enabled);
            setExportPackage(draft.config.export_package);
            setProvider(draft.config.provider ?? "");
            setBaseUrl(draft.config.base_url ?? "");
            setSimpleModel(draft.config.simple_model ?? "");
            setComplexModel(draft.config.complex_model ?? "");
            setTimeoutSeconds(
              draft.config.timeout_seconds == null ? "" : String(draft.config.timeout_seconds),
            );
          }
        }
        setError(null);
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

    void load();
    return () => {
      cancelled = true;
    };
  }, [initialDraftId]);

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? null,
    [selectedTemplateId, templates],
  );
  const activeProvider = (provider || defaultProvider) as ProviderName;
  const activeProviderSettings =
    activeProvider === "heuristic" ? null : providerSettings[activeProvider];

  function updateDefaultProviderField(field: keyof ProviderFormState, value: string) {
    if (defaultProvider === "heuristic") {
      return;
    }
    setProviderSettings((current) => ({
      ...current,
      [defaultProvider]: {
        ...current[defaultProvider],
        [field]: value,
      },
    }));
  }

  async function handleSaveRuntimeConfig() {
    setIsSavingRuntimeConfig(true);
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
      setIsSavingRuntimeConfig(false);
    }
  }

  async function handleSaveConfig() {
    if (!initialDraftId || !selectedTemplateId) {
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const saved = await saveCourseDraftConfig(initialDraftId, {
        template_id: selectedTemplateId,
        content_density: contentDensity,
        review_mode: reviewMode,
        review_enabled: reviewEnabled,
        export_package: exportPackage,
        provider: (provider || null) as ProviderName | null,
        base_url: baseUrl.trim() || null,
        simple_model: simpleModel.trim() || null,
        complex_model: complexModel.trim() || null,
        timeout_seconds: timeoutSeconds.trim() ? Number(timeoutSeconds) : null,
      });
      setDraftConfig(saved);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unknown error");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCreateRun(kind: "chapter" | "global") {
    if (!initialDraftId) {
      return;
    }
    if (kind === "chapter") {
      setIsStartingRun(true);
    } else {
      setIsStartingGlobalRun(true);
    }
    setError(null);
    try {
      const run = await createRun(initialDraftId, {
        review_enabled: reviewEnabled,
        run_kind: kind,
      });
      router.push(
        `/runs/${run.id}?draftId=${encodeURIComponent(run.draft_id)}&courseId=${encodeURIComponent(run.course_id)}`,
      );
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Unknown error");
    } finally {
      setIsStartingRun(false);
      setIsStartingGlobalRun(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--stitch-background)] text-[var(--stitch-on-surface)]">
      <StitchV4TopNav
        active="config"
        context={{
          draftId: initialDraftId,
          courseId: draftCourseId ?? context.courseId,
          runId: context.runId,
        }}
      />
      <main className="flex min-h-[calc(100vh-64px)]">
        <section className="flex-1 px-8 py-8 pr-92">
          <div className="mx-auto max-w-7xl">
          <header className="mb-10">
            <h1 className="font-stitch-headline mb-4 text-5xl font-extrabold tracking-[-0.08em]">
              {messages.config.title}
            </h1>
            <p className="max-w-2xl font-medium text-[var(--stitch-on-surface-variant)]">
              {messages.config.subtitle}
            </p>
          </header>

          {isLoading ? (
            <div className="rounded-2xl bg-[var(--stitch-surface-container-low)] p-8 text-sm text-[var(--stitch-on-surface-variant)]">
              {messages.config.loading}
            </div>
          ) : (
            <div className="items-start gap-8 lg:grid lg:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.9fr)]">
              <div className="space-y-12">
                <section className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h2 className="font-stitch-headline text-2xl font-bold">{messages.config.densityTitle}</h2>
                    <span className="rounded bg-[rgba(29,109,255,0.1)] px-2 py-1 text-xs font-bold uppercase text-[var(--stitch-primary-container)]">
                      {messages.config.densityBadge}
                    </span>
                  </div>
                  <div className="grid gap-6 md:grid-cols-3">
                    {[
                      ["light", "flight", messages.config.density.light.title, messages.config.density.light.description],
                      ["balanced", "balance", messages.config.density.balanced.title, messages.config.density.balanced.description],
                      ["dense", "grid_view", messages.config.density.dense.title, messages.config.density.dense.description],
                    ].map(([value, icon, title, description]) => {
                      const selected = contentDensity === value;
                      return (
                        <button
                          key={value}
                          type="button"
                          onClick={() => setContentDensity(value)}
                          className={`rounded-xl p-6 text-left transition-all ${
                            selected
                              ? "scale-[1.02] bg-[var(--stitch-primary-container)] text-white shadow-xl shadow-[rgba(0,85,212,0.1)] ring-2 ring-[var(--stitch-primary)]"
                              : "bg-[var(--stitch-surface-container-lowest)] ring-1 ring-[rgba(194,198,216,0.25)] hover:bg-[var(--stitch-surface-container-high)]"
                          }`}
                        >
                          <StitchV4MaterialSymbol
                            name={icon}
                            className={`mb-4 ${
                              selected ? "text-white" : "text-[var(--stitch-on-surface-variant)]"
                            }`}
                          />
                          <h3 className="mb-2 text-lg font-bold">{title}</h3>
                          <p
                            className={`text-sm ${
                              selected ? "opacity-90" : "text-[var(--stitch-on-surface-variant)]"
                            }`}
                          >
                            {description}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                </section>

                <section className="rounded-2xl bg-[var(--stitch-surface-container-low)] p-8">
                  <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                    <div className="flex items-center gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--stitch-surface-container-highest)]">
                        <StitchV4MaterialSymbol name="fact_check" />
                      </div>
                      <div>
                        <h2 className="font-stitch-headline text-xl font-bold">{messages.config.reviewTitle}</h2>
                        <p className="text-sm text-[var(--stitch-on-surface-variant)]">
                          {copy.reviewEnabledHelpText}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 rounded-full bg-[var(--stitch-surface-container-high)] p-1.5">
                      <button
                        type="button"
                        onClick={() => setReviewEnabled(false)}
                        className={`rounded-full px-4 py-1.5 text-xs font-bold ${
                          !reviewEnabled
                            ? "bg-[var(--stitch-surface-container-lowest)] text-[var(--stitch-on-surface-variant)]"
                            : "text-[var(--stitch-on-surface-variant)]"
                        }`}
                      >
                        {messages.config.reviewDisabled}
                      </button>
                      <button
                        type="button"
                        onClick={() => setReviewEnabled(true)}
                        className={`rounded-full px-4 py-1.5 text-xs font-bold ${
                          reviewEnabled
                            ? "bg-[var(--stitch-primary)] text-white"
                            : "text-[var(--stitch-on-surface-variant)]"
                        }`}
                      >
                        {messages.config.reviewEnabled}
                      </button>
                    </div>
                  </div>

                  <div className="mt-8 grid gap-8 md:grid-cols-2">
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-[var(--stitch-secondary)]">
                        {messages.config.strategyLabel}
                      </label>
                      <div className="relative">
                        <select
                          value={reviewMode}
                          onChange={(event) => setReviewMode(event.target.value)}
                          className="w-full appearance-none rounded-xl bg-[var(--stitch-surface-container-high)] px-4 py-4 text-sm font-medium outline-none"
                        >
                          <option value="light">{messages.config.strategyOptions.light}</option>
                          <option value="strict">{messages.config.strategyOptions.strict}</option>
                          <option value="fast">{messages.config.strategyOptions.fast}</option>
                        </select>
                        <StitchV4MaterialSymbol
                          name="expand_more"
                          className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-[var(--stitch-secondary)]">
                        {messages.config.templateLabel}
                      </label>
                      <div className="relative">
                        <select
                          value={selectedTemplateId}
                          onChange={(event) => setSelectedTemplateId(event.target.value)}
                          className="w-full appearance-none rounded-xl bg-[var(--stitch-surface-container-high)] px-4 py-4 text-sm font-medium outline-none"
                        >
                          {templates.map((template) => (
                            <option key={template.id} value={template.id}>
                              {template.name}
                            </option>
                          ))}
                        </select>
                        <StitchV4MaterialSymbol
                          name="expand_more"
                          className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2"
                        />
                      </div>
                    </div>
                  </div>
                </section>

                <div className="flex flex-wrap items-center justify-end gap-4 pt-2">
                  <button
                    type="button"
                    onClick={() => void handleSaveConfig()}
                    disabled={!initialDraftId || isSaving}
                    className="rounded-full px-8 py-3 font-bold text-[var(--stitch-on-surface)] hover:bg-[var(--stitch-surface-container-high)]"
                  >
                    {isSaving ? messages.config.saveConfigBusy : messages.config.saveConfig}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleCreateRun("chapter")}
                    disabled={!initialDraftId || isStartingRun}
                    className="rounded-full bg-gradient-to-r from-[var(--stitch-primary)] to-[var(--stitch-primary-container)] px-8 py-3 font-bold text-white shadow-lg shadow-[rgba(0,85,212,0.2)]"
                  >
                    {isStartingRun ? messages.config.startRunBusy : messages.config.startRun}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleCreateRun("global")}
                    disabled={!initialDraftId || isStartingGlobalRun}
                    className="rounded-full bg-[var(--stitch-inverse-surface)] px-8 py-3 font-bold text-white"
                  >
                    {isStartingGlobalRun ? messages.config.updateGlobalBusy : messages.config.updateGlobal}
                  </button>
                </div>

                {error ? (
                  <div className="rounded-xl bg-[var(--stitch-error-container)] px-4 py-3 text-sm text-[var(--stitch-on-error-container)]">
                    {error}
                  </div>
                ) : null}
              </div>

              <aside className="mt-10 rounded-2xl bg-[var(--stitch-surface-container-lowest)] p-8 ring-1 ring-[rgba(194,198,216,0.15)] lg:mt-0">
                <div className="mb-6">
                  <h2 className="font-stitch-headline text-2xl font-bold">
                    {copy.runtimeDefaultsTitle}
                  </h2>
                  <p className="mt-3 text-sm text-[var(--stitch-on-surface-variant)]">
                    {copy.runtimeDefaultsHelpText}
                  </p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-1">
                  <div className="space-y-2 md:col-span-2 lg:col-span-1">
                    <label className="text-xs font-bold uppercase tracking-wider text-[var(--stitch-on-surface-variant)]">
                      {messages.config.defaultProviderLabel}
                    </label>
                    <select
                      value={defaultProvider}
                      onChange={(event) => setDefaultProvider(event.target.value as ProviderName)}
                      className="w-full rounded-xl bg-[var(--stitch-surface-container-low)] px-4 py-3 outline-none"
                    >
                      <option value="heuristic">heuristic</option>
                      <option value="openai">OpenAI</option>
                      <option value="openai_compatible">OpenAI-compatible</option>
                      <option value="anthropic">Anthropic</option>
                    </select>
                  </div>
                  {defaultProvider !== "heuristic"
                    ? (["api_key", "base_url", "simple_model", "complex_model", "timeout_seconds"] as const).map((field) => (
                        <div
                          key={field}
                          className={field === "api_key" ? "space-y-2 md:col-span-2 lg:col-span-1" : "space-y-2"}
                        >
                          <label className="text-xs font-bold uppercase tracking-wider text-[var(--stitch-on-surface-variant)]">
                            {field}
                          </label>
                          <input
                            value={providerSettings[defaultProvider][field]}
                            onChange={(event) => updateDefaultProviderField(field, event.target.value)}
                            className="w-full rounded-xl bg-[var(--stitch-surface-container-low)] px-4 py-3 outline-none"
                          />
                        </div>
                      ))
                    : null}
                </div>
                <div className="mt-6 flex justify-end">
                  <button
                    type="button"
                    onClick={() => void handleSaveRuntimeConfig()}
                    disabled={isSavingRuntimeConfig}
                    className="rounded-full bg-[var(--stitch-inverse-surface)] px-8 py-3 text-sm font-bold text-white"
                  >
                    {isSavingRuntimeConfig ? messages.config.saveAiConfigBusy : messages.config.saveAiConfig}
                  </button>
                </div>
              </aside>
            </div>
          )}
          </div>
        </section>

        <StitchV4RightRail title={messages.common.context} subtitle={messages.common.activeSession}>
          <StitchV4ContextRail
            draftId={initialDraftId}
            courseId={draftCourseId ?? context.courseId}
            runId={context.runId}
            prefix={
              <section className="rounded-xl bg-[#474746] p-5">
                <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-[#dddad0]/70">
                  {messages.config.summaryTitle}
                </h3>
                <div className="space-y-3 text-sm text-[#f4f1e7]">
                  <div>{messages.config.summaryTarget} · {selectedTemplate?.expected_outputs.join(", ") || messages.common.pending}</div>
                  <div>{messages.config.summaryReview} · {reviewEnabled ? reviewMode : messages.config.disabled}</div>
                  <div>{messages.config.summaryProvider} · {providerLabel(activeProvider)}</div>
                  <div>
                    {messages.config.summaryModels} · {simpleModel || activeProviderSettings?.simple_model || messages.common.notConfigured} /{" "}
                    {complexModel || activeProviderSettings?.complex_model || messages.common.notConfigured}
                  </div>
                  <div>{messages.config.summarySaved} · {draftConfig ? messages.config.saved : messages.config.unsaved}</div>
                </div>
              </section>
            }
          />
        </StitchV4RightRail>
      </main>
    </div>
  );
}
