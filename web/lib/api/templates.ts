export type TemplatePreset = {
  id: string;
  name: string;
  description: string;
  expected_outputs: string[];
};

export type ProviderName = "heuristic" | "openai" | "openai_compatible" | "anthropic";

export type HostedProviderSettings = {
  api_key: string | null;
  base_url: string | null;
  simple_model: string | null;
  complex_model: string | null;
  timeout_seconds: number | null;
};

export type GuiRuntimeConfig = {
  default_provider: ProviderName;
  providers: {
    openai: HostedProviderSettings;
    openai_compatible: HostedProviderSettings;
    anthropic: HostedProviderSettings;
  };
};

export type DraftConfig = {
  draft_id: string;
  template: TemplatePreset;
  content_density: string;
  review_mode: string;
  review_enabled: boolean;
  export_package: boolean;
  provider: ProviderName | null;
  base_url: string | null;
  simple_model: string | null;
  complex_model: string | null;
  timeout_seconds: number | null;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function listTemplates(): Promise<TemplatePreset[]> {
  const response = await fetch(`${API_BASE_URL}/templates`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to load templates: ${response.status}`);
  }

  return (await response.json()) as TemplatePreset[];
}

export async function getGuiRuntimeConfig(): Promise<GuiRuntimeConfig> {
  const response = await fetch(`${API_BASE_URL}/gui-runtime-config`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to load GUI runtime config: ${response.status}`);
  }

  return (await response.json()) as GuiRuntimeConfig;
}

export async function saveGuiRuntimeConfig(payload: GuiRuntimeConfig): Promise<GuiRuntimeConfig> {
  const response = await fetch(`${API_BASE_URL}/gui-runtime-config`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to save GUI runtime config: ${response.status}`);
  }

  return (await response.json()) as GuiRuntimeConfig;
}

export async function saveCourseDraftConfig(
  draftId: string,
  payload: {
    template_id: string;
    content_density: string;
    review_mode: string;
    review_enabled: boolean;
    export_package: boolean;
    provider?: ProviderName | null;
    base_url?: string | null;
    simple_model?: string | null;
    complex_model?: string | null;
    timeout_seconds?: number | null;
  },
): Promise<DraftConfig> {
  const response = await fetch(`${API_BASE_URL}/course-drafts/${draftId}/config`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to save draft config: ${response.status}`);
  }

  return (await response.json()) as DraftConfig;
}
