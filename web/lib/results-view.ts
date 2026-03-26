import type { ArtifactNode } from "@/lib/api/artifacts";

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
