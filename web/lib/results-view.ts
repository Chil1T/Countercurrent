import type { ArtifactNode } from "@/lib/api/artifacts";
import type { ResultsSnapshot } from "@/lib/api/artifacts";

type ArtifactTreeFileNode = {
  key: string;
  label: string;
  path: string;
};

type ArtifactTreeFolderNode = {
  key: string;
  label: string;
  children: ArtifactTreeNode[];
};

export type ArtifactTreeNode = ArtifactTreeFileNode | ArtifactTreeFolderNode;

export type ArtifactTreeSection = {
  key: "chapter" | "global" | "runtime";
  label: string;
  children: ArtifactTreeNode[];
};

export type ResultsTreeFileNode = {
  key: string;
  label: string;
  path: string;
  sourceCourseId: string;
  runId: string;
};

export type ResultsTreeFolderNode = {
  key: string;
  label: string;
  children: ResultsTreeNode[];
};

export type ResultsTreeNode = ResultsTreeFileNode | ResultsTreeFolderNode;

export type ResultsTreeSection = {
  key: "historical-courses" | "current-course";
  label: string;
  children: ResultsTreeNode[];
};

export type ResultsSnapshotSelectionInput = {
  sourceCourseId: string;
  runId: string;
  path: string;
};

function getArtifactGroupKey(path: string): "chapter" | "intermediate" | "global" | "review" | "runtime" {
  if (path.includes("review_report.json")) {
    return "review";
  }
  if (path.startsWith("global/")) {
    return "global";
  }
  if (path.includes("/intermediate/")) {
    return "intermediate";
  }
  if (path.startsWith("chapters/")) {
    return "chapter";
  }
  return "runtime";
}

export function getArtifactDisplayName(path: string): string {
  const segments = path.split("/");
  return segments[segments.length - 1] ?? path;
}

export function getArtifactGroupLabel(path: string): string {
  const key = getArtifactGroupKey(path);
  return {
    chapter: "章节产物",
    intermediate: "中间数据",
    global: "全局汇总",
    review: "Review",
    runtime: "运行文件",
  }[key];
}

export function getArtifactTreeCardClass(_path: string, selected: boolean): string {
  if (selected) {
    return "border border-stone-900 bg-stone-900 text-white shadow-sm";
  }

  return "border border-stone-200 bg-stone-50 text-stone-700 hover:bg-stone-100";
}

export function isArtifactTreeLoading(runStatus: string | null | undefined): boolean {
  if (!runStatus) {
    return false;
  }

  return !new Set(["completed", "failed", "cleaned"]).has(runStatus);
}

export function buildResultsSnapshotSelection(input: ResultsSnapshotSelectionInput): string {
  return `${input.sourceCourseId}::${input.runId}::${input.path}`;
}

export function parseResultsSnapshotSelection(selection: string): ResultsSnapshotSelectionInput | null {
  const [sourceCourseId, runId, ...pathParts] = selection.split("::");
  const path = pathParts.join("::");
  if (!sourceCourseId || !runId || !path) {
    return null;
  }
  return { sourceCourseId, runId, path };
}

export function getResultsTreeSelectionAncestors(selection: string): string[] {
  const parsed = parseResultsSnapshotSelection(selection);
  if (!parsed) {
    return [];
  }
  const chapterId = parsed.path.split("/")[1] ?? "chapter";
  const rootKey = parsed.sourceCourseId === "__current__" ? "current-course" : parsed.sourceCourseId;
  return [rootKey, parsed.runId, `${parsed.runId}:${chapterId}`];
}

export function findResultsTreeNodeBySelection(
  nodes: ResultsTreeNode[] | ResultsTreeSection[],
  selection: string,
): ResultsTreeNode | null {
  for (const node of nodes) {
    if ("path" in node && node.key === selection) {
      return node;
    }
    if ("children" in node) {
      const child = findResultsTreeNodeBySelection(node.children, selection);
      if (child) {
        return child;
      }
    }
  }
  return null;
}

function buildRunTreeNodes(
  sourceCourseId: string,
  runId: string,
  chapters: Array<{ chapter_id: string; files: Array<{ path: string; kind: string; size: number }> }>,
  markCurrentRun: boolean,
): ResultsTreeFolderNode {
  return {
    key: runId,
    label: markCurrentRun ? `${runId} · 当前 run` : runId,
    children: chapters.map((chapter) => ({
      key: `${runId}:${chapter.chapter_id}`,
      label: chapter.chapter_id,
      children: chapter.files
        .filter((file) => file.path.endsWith(".md"))
        .map((file) => ({
          key: buildResultsSnapshotSelection({
            sourceCourseId,
            runId,
            path: file.path,
          }),
          label: getArtifactDisplayName(file.path),
          path: file.path,
          sourceCourseId,
          runId,
        })),
    })),
  };
}

export function buildResultsSnapshotTree(
  snapshot: ResultsSnapshot,
  currentRunId: string | null = null,
): ResultsTreeSection[] {
  return [
    {
      key: "historical-courses",
      label: "过去课程产物",
      children: snapshot.historical_courses.map((course) => ({
        key: course.course_id,
        label: course.course_id,
        children: course.runs.map((run) =>
          buildRunTreeNodes(course.course_id, run.run_id, run.chapters, false),
        ),
      })),
    },
    {
      key: "current-course",
      label: "当前课程产物",
      children: snapshot.current_course_runs.map((run) =>
        buildRunTreeNodes(
          "__current__",
          run.run_id,
          run.chapters,
          currentRunId === run.run_id,
        ),
      ),
    },
  ];
}

export function getArtifactTreePathAncestors(path: string): string[] {
  if (path.startsWith("chapters/")) {
    const segments = path.split("/");
    const chapterId = segments[1] ?? "chapter";
    const bucket = segments[2] === "intermediate" ? "intermediate" : "final";
    return ["chapter", chapterId, `${chapterId}:${bucket}`];
  }

  if (path.startsWith("global/")) {
    return ["global"];
  }

  return ["runtime"];
}

export function buildArtifactTree(nodes: ArtifactNode[]): ArtifactTreeSection[] {
  const chapterGroups = new Map<
    string,
    {
      final: ArtifactTreeFileNode[];
      intermediate: ArtifactTreeFileNode[];
    }
  >();
  const globalFiles: ArtifactTreeFileNode[] = [];
  const runtimeFiles: ArtifactTreeFileNode[] = [];

  for (const node of nodes) {
    const treeNode: ArtifactTreeFileNode = {
      key: node.path,
      label: getArtifactDisplayName(node.path),
      path: node.path,
    };

    if (node.path.startsWith("chapters/")) {
      const segments = node.path.split("/");
      const chapterId = segments[1] ?? "chapter";
      const chapterGroup =
        chapterGroups.get(chapterId) ?? {
          final: [],
          intermediate: [],
        };
      const bucket = segments[2] === "intermediate" ? "intermediate" : "final";
      chapterGroup[bucket].push(treeNode);
      chapterGroups.set(chapterId, chapterGroup);
      continue;
    }

    if (node.path.startsWith("global/")) {
      globalFiles.push(treeNode);
      continue;
    }

    runtimeFiles.push(treeNode);
  }

  return [
    {
      key: "chapter",
      label: "章节产物",
      children: [...chapterGroups.entries()].map(([chapterId, chapterGroup]) => {
        const children: ArtifactTreeNode[] = [];
        if (chapterGroup.final.length > 0) {
          children.push({
            key: `${chapterId}:final`,
            label: "最终产物",
            children: chapterGroup.final,
          });
        }
        if (chapterGroup.intermediate.length > 0) {
          children.push({
            key: `${chapterId}:intermediate`,
            label: "中间数据",
            children: chapterGroup.intermediate,
          });
        }

        return {
          key: chapterId,
          label: chapterId,
          children,
        };
      }),
    },
    {
      key: "global",
      label: "全局汇总",
      children: globalFiles,
    },
    {
      key: "runtime",
      label: "运行文件",
      children: runtimeFiles,
    },
  ];
}

export function findArtifactTreeNodeByPath(
  nodes: ArtifactTreeNode[],
  path: string,
): ArtifactTreeNode | null {
  for (const node of nodes) {
    if ("path" in node && node.path === path) {
      return node;
    }
    if ("children" in node) {
      const child = findArtifactTreeNodeByPath(node.children, path);
      if (child) {
        return child;
      }
    }
  }

  return null;
}
