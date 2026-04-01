"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { getCourseDraft } from "@/lib/api/course-drafts";
import { createRun } from "@/lib/api/runs";
import { getConfigWorkbenchCopy, getConfigWorkbenchLayout } from "@/lib/config-workbench-view";
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
import { ConfigV2Sections, ProviderFormState } from "@/components/config/config-v2-sections";

type ProviderSettingsMap = {
  openai: ProviderFormState;
  openai_compatible: ProviderFormState;
  anthropic: ProviderFormState;
};

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

export function TemplateConfigWorkbenchV2() {
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
    <ConfigV2Sections
      isLoading={isLoading}
      templates={templates}
      selectedTemplateId={selectedTemplateId}
      selectedTemplate={selectedTemplate}
      contentDensity={contentDensity}
      reviewMode={reviewMode}
      reviewEnabled={reviewEnabled}
      exportPackage={exportPackage}
      defaultProvider={defaultProvider}
      activeDefaultProviderSettings={activeDefaultProviderSettings}
      isSavingRuntimeDefaults={isSavingRuntimeDefaults}
      runtimeDefaultsTitle={configWorkbenchCopy.runtimeDefaultsTitle}
      runtimeDefaultsHelpText={configWorkbenchCopy.runtimeDefaultsHelpText}
      runtimeDefaultsDefaultOpen={configWorkbenchLayout.runtimeDefaultsDefaultOpen}
      runReviewOverride={runReviewOverride}
      draftId={draftId}
      isSaving={isSaving}
      isStartingRun={isStartingRun}
      isStartingGlobalRun={isStartingGlobalRun}
      savedConfig={savedConfig}
      error={error}
      effectiveProviderLabel={providerLabel(effectiveProvider)}
      effectiveSimpleModel={courseSimpleModel || effectiveRuntimeDefaults?.simple_model || "未设置"}
      effectiveComplexModel={courseComplexModel || effectiveRuntimeDefaults?.complex_model || "未设置"}
      onSelectTemplate={setSelectedTemplateId}
      onContentDensityChange={setContentDensity}
      onReviewModeChange={setReviewMode}
      onReviewEnabledChange={setReviewEnabled}
      onExportPackageChange={setExportPackage}
      onDefaultProviderChange={setDefaultProvider}
      onProviderFieldChange={(field, value) =>
        updateProviderSettings(defaultProvider as keyof ProviderSettingsMap, field, value)
      }
      onSaveRuntimeDefaults={() => void handleSaveRuntimeDefaults()}
      onRunReviewOverrideChange={setRunReviewOverride}
      onSave={() => void handleSave()}
      onStartRun={() => void handleStartRun()}
      onStartGlobalRun={() => void handleStartGlobalRun()}
    />
  );
}
