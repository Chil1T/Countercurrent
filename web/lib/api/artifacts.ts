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

export type ResultsSnapshotFile = {
  path: string;
  kind: string;
  size: number;
};

export type ResultsSnapshotChapter = {
  chapter_id: string;
  files: ResultsSnapshotFile[];
};

export type ResultsSnapshotRun = {
  run_id: string;
  chapters: ResultsSnapshotChapter[];
};

export type ResultsSnapshotCourse = {
  course_id: string;
  runs: ResultsSnapshotRun[];
};

export type ResultsSnapshot = {
  current_course_id: string | null;
  current_course_runs: ResultsSnapshotRun[];
  historical_courses: ResultsSnapshotCourse[];
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

export async function getResultsSnapshot(courseId: string): Promise<ResultsSnapshot> {
  const response = await fetch(`${API_BASE_URL}/courses/${courseId}/results-snapshot`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to load results snapshot: ${response.status}`);
  }
  return (await response.json()) as ResultsSnapshot;
}

export async function getGlobalResultsSnapshot(): Promise<ResultsSnapshot> {
  const response = await fetch(`${API_BASE_URL}/results-snapshot`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to load global results snapshot: ${response.status}`);
  }
  return (await response.json()) as ResultsSnapshot;
}

export type ResultsSnapshotContentRequest = {
  sourceCourseId?: string | null;
  runId: string;
  path: string;
};

export type GlobalResultsSnapshotContentRequest = {
  sourceCourseId: string;
  runId: string;
  path: string;
};

export function buildResultsSnapshotContentUrl(
  courseId: string,
  request: ResultsSnapshotContentRequest,
): string {
  const params = new URLSearchParams();
  if (request.sourceCourseId) {
    params.set("source_course_id", request.sourceCourseId);
  }
  params.set("run_id", request.runId);
  params.set("path", request.path);
  return `${API_BASE_URL}/courses/${courseId}/results-snapshot/content?${params.toString()}`;
}

export function buildGlobalResultsSnapshotContentUrl(
  request: GlobalResultsSnapshotContentRequest,
): string {
  const params = new URLSearchParams();
  params.set("source_course_id", request.sourceCourseId);
  params.set("run_id", request.runId);
  params.set("path", request.path);
  return `${API_BASE_URL}/results-snapshot/content?${params.toString()}`;
}

export async function getResultsSnapshotContent(
  courseId: string,
  request: ResultsSnapshotContentRequest,
): Promise<ArtifactContent> {
  const response = await fetch(buildResultsSnapshotContentUrl(courseId, request), {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to load results snapshot content: ${response.status}`);
  }
  return (await response.json()) as ArtifactContent;
}

export async function getGlobalResultsSnapshotContent(
  request: GlobalResultsSnapshotContentRequest,
): Promise<ArtifactContent> {
  const response = await fetch(buildGlobalResultsSnapshotContentUrl(request), {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to load global results snapshot content: ${response.status}`);
  }
  return (await response.json()) as ArtifactContent;
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
