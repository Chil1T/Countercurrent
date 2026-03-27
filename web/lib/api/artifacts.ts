export type ArtifactNode = {
  path: string;
  kind: string;
  size: number;
};

export type ArtifactTree = {
  course_id: string;
  nodes: ArtifactNode[];
};

export type ArtifactContent = {
  path: string;
  kind: string;
  content: string;
};

export type ReviewSummary = {
  course_id: string;
  report_count: number;
  issue_count: number;
  reports: Array<{
    path: string;
    status: string;
    issues: Array<
      | string
      | {
          severity?: string | null;
          issue_type?: string | null;
          location?: string | null;
          fix_hint?: string | null;
          detail?: Record<string, unknown> | null;
        }
    >;
  }>;
};

export type ExportUrlOptions = {
  cacheBust?: string;
  completedChaptersOnly?: boolean;
  finalOutputsOnly?: boolean;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function getArtifactTree(courseId: string): Promise<ArtifactTree> {
  const response = await fetch(`${API_BASE_URL}/courses/${courseId}/artifacts/tree`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to load artifact tree: ${response.status}`);
  }
  return (await response.json()) as ArtifactTree;
}

export async function getArtifactContent(
  courseId: string,
  path: string,
): Promise<ArtifactContent> {
  const response = await fetch(
    `${API_BASE_URL}/courses/${courseId}/artifacts/content?path=${encodeURIComponent(path)}`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    throw new Error(`Failed to load artifact content: ${response.status}`);
  }
  return (await response.json()) as ArtifactContent;
}

export async function getReviewSummary(courseId: string): Promise<ReviewSummary> {
  const response = await fetch(`${API_BASE_URL}/courses/${courseId}/review-summary`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to load review summary: ${response.status}`);
  }
  return (await response.json()) as ReviewSummary;
}

export function buildExportUrl(
  courseId: string,
  cacheBustOrOptions?: string | ExportUrlOptions,
): string {
  const base = `${API_BASE_URL}/courses/${courseId}/export`;
  const options =
    typeof cacheBustOrOptions === "string"
      ? { cacheBust: cacheBustOrOptions }
      : (cacheBustOrOptions ?? {});
  const params = new URLSearchParams();
  if (options.cacheBust) {
    params.set("v", options.cacheBust);
  }
  if (options.completedChaptersOnly) {
    params.set("completed_chapters_only", "true");
  }
  if (options.finalOutputsOnly) {
    params.set("final_outputs_only", "true");
  }
  const query = params.toString();
  if (!query) {
    return base;
  }
  return `${base}?${query}`;
}
