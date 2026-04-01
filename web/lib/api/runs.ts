export type StageStatus = {
  name: string;
  status: string;
};

export type ChapterProgress = {
  chapter_id: string;
  status: string;
  current_step: string | null;
  completed_step_count: number;
  total_step_count: number;
  export_ready: boolean;
};
export type CourseResultsContext = {
  course_id: string;
  latest_run: RunSession | null;
};


export type RunSession = {
  id: string;
  draft_id: string;
  course_id: string;
  created_at: string | null;
  status: string;
  run_kind: "chapter" | "global";
  backend: string;
  hosted: boolean;
  base_url: string | null;
  simple_model: string | null;
  complex_model: string | null;
  timeout_seconds: number | null;
  target_output: string | null;
  review_enabled: boolean;
  review_mode: string | null;
  stages: StageStatus[];
  chapter_progress: ChapterProgress[];
  snapshot_complete: boolean;
  last_error: string | null;
};

export type UnstartedRunWorkbenchState = {
  draft_id: string | null;
  course_id: string | null;
};

export type RunLogPreview = {
  run_id: string;
  available: boolean;
  cursor: number;
  content: string;
  truncated: boolean;
};

export type RunLogChunk = {
  run_id: string;
  cursor: number;
  content: string;
  complete: boolean;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function createRun(
  draftId: string,
  options?: {
    review_enabled?: boolean;
    run_kind?: "chapter" | "global";
  },
): Promise<RunSession> {
  const response = await fetch(`${API_BASE_URL}/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      draft_id: draftId,
      review_enabled: options?.review_enabled,
      run_kind: options?.run_kind ?? "chapter",
    }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to create run: ${response.status} ${message}`);
  }

  return (await response.json()) as RunSession;
}

export async function getRun(runId: string): Promise<RunSession> {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to load run: ${response.status} ${message}`);
  }

  return (await response.json()) as RunSession;
}

export async function resumeRun(runId: string): Promise<RunSession> {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/resume`, {
    method: "POST",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to resume run: ${response.status} ${message}`);
  }

  return (await response.json()) as RunSession;
}

export async function cleanRun(runId: string): Promise<RunSession> {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/clean`, {
    method: "POST",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to clean run: ${response.status} ${message}`);
  }

  return (await response.json()) as RunSession;
}

export async function getCourseResultsContext(courseId: string): Promise<CourseResultsContext> {
  const response = await fetch(`${API_BASE_URL}/courses/${courseId}/results-context`, {
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to load course results context: ${response.status} ${message}`);
  }

  return (await response.json()) as CourseResultsContext;
}

export async function getRunLog(runId: string): Promise<RunLogPreview> {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/log`, {
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to load run log: ${response.status} ${message}`);
  }

  return (await response.json()) as RunLogPreview;
}

export function subscribeRunLogEvents(
  runId: string,
  cursor: number,
  handlers: {
    onChunk: (chunk: RunLogChunk) => void;
    onError?: (message: string) => void;
  },
): () => void {
  const eventSource = new EventSource(`${API_BASE_URL}/runs/${runId}/log/events?cursor=${cursor}`);
  let closed = false;

  const handleChunk = (event: MessageEvent<string>) => {
    try {
      const payload = JSON.parse(event.data) as RunLogChunk;
      handlers.onChunk(payload);
      if (payload.complete) {
        closed = true;
        eventSource.close();
      }
    } catch (error) {
      handlers.onError?.(error instanceof Error ? error.message : "Failed to parse run log event");
    }
  };

  const handleError = () => {
    if (!closed) {
      handlers.onError?.("Run log stream disconnected");
    }
  };

  eventSource.addEventListener("run.log", handleChunk as EventListener);
  eventSource.onerror = handleError;

  return () => {
    closed = true;
    eventSource.removeEventListener("run.log", handleChunk as EventListener);
    eventSource.close();
  };
}

export function subscribeRunEvents(
  runId: string,
  handlers: {
    onUpdate: (run: RunSession) => void;
    onError?: (message: string) => void;
  },
): () => void {
  const eventSource = new EventSource(`${API_BASE_URL}/runs/${runId}/events`);
  let closed = false;

  const handleUpdate = (event: MessageEvent<string>) => {
    try {
      const payload = JSON.parse(event.data) as RunSession;
      handlers.onUpdate(payload);
      if (payload.status === "completed" || payload.status === "failed" || payload.status === "cleaned") {
        closed = true;
        eventSource.close();
      }
    } catch (error) {
      handlers.onError?.(error instanceof Error ? error.message : "Failed to parse run event");
    }
  };

  const handleError = () => {
    if (!closed) {
      handlers.onError?.("Run event stream disconnected");
    }
  };

  eventSource.addEventListener("run.update", handleUpdate as EventListener);
  eventSource.onerror = handleError;

  return () => {
    closed = true;
    eventSource.removeEventListener("run.update", handleUpdate as EventListener);
    eventSource.close();
  };
}
