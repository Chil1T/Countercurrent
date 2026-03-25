export type SearchParamsLike = {
  get(name: string): string | null | undefined;
};

export type ShellNavItem = {
  step: string;
  label: string;
  hint: string;
  href: string | null;
  enabled: boolean;
};

export type AppShellState = {
  courseLabel: string;
  statusLabel: string;
  navItems: ShellNavItem[];
};

function buildConfigHref(
  searchParams?: SearchParamsLike,
  runId?: string | null,
  courseId?: string | null,
): string {
  const params = new URLSearchParams();
  const draftId = searchParams?.get("draftId");
  const resolvedRunId = searchParams?.get("runId") ?? runId;
  const resolvedCourseId = searchParams?.get("courseId") ?? courseId;
  if (draftId) {
    params.set("draftId", draftId);
  }
  if (resolvedRunId) {
    params.set("runId", resolvedRunId);
  }
  if (resolvedCourseId) {
    params.set("courseId", resolvedCourseId);
  }
  const query = params.toString();
  return query ? `/courses/new/config?${query}` : "/courses/new/config";
}

function buildInputHref(
  searchParams?: SearchParamsLike,
  runId?: string | null,
  courseId?: string | null,
): string {
  const params = new URLSearchParams();
  const draftId = searchParams?.get("draftId");
  const resolvedRunId = searchParams?.get("runId") ?? runId;
  const resolvedCourseId = searchParams?.get("courseId") ?? courseId;
  if (draftId) {
    params.set("draftId", draftId);
  }
  if (resolvedRunId) {
    params.set("runId", resolvedRunId);
  }
  if (resolvedCourseId) {
    params.set("courseId", resolvedCourseId);
  }
  const query = params.toString();
  return query ? `/courses/new/input?${query}` : "/courses/new/input";
}

function buildRunHref(
  runId: string | null,
  courseId: string | null,
  searchParams?: SearchParamsLike,
): string | null {
  if (!runId) {
    return null;
  }

  const params = new URLSearchParams();
  const draftId = searchParams?.get("draftId");
  const resolvedCourseId = searchParams?.get("courseId") ?? courseId;
  if (draftId) {
    params.set("draftId", draftId);
  }
  if (resolvedCourseId) {
    params.set("courseId", resolvedCourseId);
  }

  const query = params.toString();
  return query
    ? `/runs/${encodeURIComponent(runId)}?${query}`
    : `/runs/${encodeURIComponent(runId)}`;
}

function buildResultsHref(
  courseId: string | null,
  runId: string | null,
  searchParams?: SearchParamsLike,
): string | null {
  if (!courseId) {
    return null;
  }

  const params = new URLSearchParams();
  const draftId = searchParams?.get("draftId");
  const resolvedRunId = searchParams?.get("runId") ?? runId;
  if (draftId) {
    params.set("draftId", draftId);
  }
  if (resolvedRunId) {
    params.set("runId", resolvedRunId);
  }

  const query = params.toString();
  return query
    ? `/courses/${encodeURIComponent(courseId)}/results?${query}`
    : `/courses/${encodeURIComponent(courseId)}/results`;
}

export function buildAppShellState(
  pathname: string,
  searchParams?: SearchParamsLike,
): AppShellState {
  const runMatch = pathname.match(/^\/runs\/([^/]+)$/);
  const resultMatch = pathname.match(/^\/courses\/([^/]+)\/results$/);

  const runId =
    runMatch?.[1] ? decodeURIComponent(runMatch[1]) : searchParams?.get("runId") ?? null;
  const courseId =
    resultMatch?.[1]
      ? decodeURIComponent(resultMatch[1])
      : searchParams?.get("courseId") ?? null;

  const statusLabel = (() => {
    if (pathname.startsWith("/courses/new/input")) {
      return "Input";
    }
    if (pathname.startsWith("/courses/new/config")) {
      return "Config";
    }
    if (pathname.startsWith("/runs/")) {
      return "Run";
    }
    if (pathname.includes("/results")) {
      return "Results";
    }
    return "Draft";
  })();

  return {
    courseLabel: courseId ?? "未绑定课程",
    statusLabel,
    navItems: [
      {
        step: "01",
        label: "输入",
        hint: "课程链接、素材、教材",
        href: buildInputHref(searchParams, runId, courseId),
        enabled: true,
      },
      {
        step: "02",
        label: "配置",
        hint: "模板与参数",
        href: buildConfigHref(searchParams, runId, courseId),
        enabled: true,
      },
      {
        step: "03",
        label: "运行",
        hint: "阶段状态与数据通路",
        href: buildRunHref(runId, courseId, searchParams),
        enabled: !!runId,
      },
      {
        step: "04",
        label: "结果",
        hint: "文件树、预览、导出",
        href: buildResultsHref(courseId, runId, searchParams),
        enabled: !!courseId,
      },
    ],
  };
}
