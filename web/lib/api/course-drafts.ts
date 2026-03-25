export type InputSlot = {
  kind: string;
  label: string;
  supported: boolean;
  count: number;
};

export type CourseDraft = {
  id: string;
  course_id: string;
  book_title: string;
  course_url: string | null;
  runtime_ready: boolean;
  config: {
    draft_id: string;
    template: {
      id: string;
      name: string;
      description: string;
      expected_outputs: string[];
    };
    content_density: string;
    review_mode: string;
    review_enabled: boolean;
    export_package: boolean;
    provider: "heuristic" | "openai" | "openai_compatible" | "anthropic" | null;
    base_url: string | null;
    simple_model: string | null;
    complex_model: string | null;
    timeout_seconds: number | null;
  } | null;
  detected: {
    course_name: string;
    textbook_title: string;
    chapter_count: number | null;
    asset_completeness: number;
  };
  input_slots: InputSlot[];
};

export type CreateCourseDraftRequest = {
  book_title: string;
  course_url?: string;
  subtitle_text?: string;
  subtitle_assets?: Array<{
    filename: string;
    content: string;
  }>;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function createCourseDraft(
  payload: CreateCourseDraftRequest | FormData,
): Promise<CourseDraft> {
  const isFormData = payload instanceof FormData;
  const response = await fetch(`${API_BASE_URL}/course-drafts`, {
    method: "POST",
    headers: isFormData
      ? undefined
      : {
          "Content-Type": "application/json",
        },
    body: isFormData ? payload : JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to create course draft: ${response.status} ${message}`);
  }

  return (await response.json()) as CourseDraft;
}

export async function getCourseDraft(draftId: string): Promise<CourseDraft> {
  const response = await fetch(`${API_BASE_URL}/course-drafts/${draftId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to load course draft: ${response.status} ${message}`);
  }

  return (await response.json()) as CourseDraft;
}
