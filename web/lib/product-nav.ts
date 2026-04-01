export type ProductNavKey = "overview" | "input" | "config" | "run" | "results";

export type ProductContext = {
  draftId?: string | null;
  courseId?: string | null;
  runId?: string | null;
};

export type ProductNavItem = {
  key: ProductNavKey;
  label: string;
  href: string;
};

function buildQuery(params: ProductContext): string {
  const query = new URLSearchParams();
  if (params.draftId) {
    query.set("draftId", params.draftId);
  }
  if (params.courseId) {
    query.set("courseId", params.courseId);
  }
  if (params.runId) {
    query.set("runId", params.runId);
  }
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}

export function buildProductHref(target: ProductNavKey, context: ProductContext): string {
  if (target === "overview") {
    return "/";
  }

  if (target === "input") {
    return `/courses/new/input${buildQuery(context)}`;
  }

  if (target === "config") {
    return `/courses/new/config${buildQuery(context)}`;
  }

  if (target === "run") {
    if (context.runId) {
      return `/runs/${context.runId}${buildQuery({
        draftId: context.draftId,
        courseId: context.courseId,
      })}`;
    }
    return `/runs${buildQuery({
      draftId: context.draftId,
      courseId: context.courseId,
    })}`;
  }

  if (context.courseId) {
    return `/courses/${context.courseId}/results${buildQuery({
      draftId: context.draftId,
      runId: context.runId,
    })}`;
  }

  return `/courses/results${buildQuery({
    draftId: context.draftId,
    courseId: context.courseId,
    runId: context.runId,
  })}`;
}

export function buildProductNav(context: ProductContext): ProductNavItem[] {
  return [
    { key: "overview", label: "overview", href: buildProductHref("overview", context) },
    { key: "input", label: "input", href: buildProductHref("input", context) },
    { key: "config", label: "config", href: buildProductHref("config", context) },
    { key: "run", label: "run", href: buildProductHref("run", context) },
    { key: "results", label: "results", href: buildProductHref("results", context) },
  ];
}
