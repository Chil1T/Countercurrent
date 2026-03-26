import type { RunSession } from "@/lib/api/runs";

function stageStatuses(run: RunSession | null): string {
  if (!run) {
    return "";
  }
  return run.stages.map((stage) => `${stage.name}:${stage.status}`).join("|");
}

export function shouldRefreshArtifactsOnRunUpdate(previousRun: RunSession | null, nextRun: RunSession): boolean {
  if (previousRun === null) {
    return true;
  }

  if (previousRun.status !== nextRun.status) {
    return true;
  }

  if (previousRun.last_error !== nextRun.last_error) {
    return true;
  }

  return stageStatuses(previousRun) !== stageStatuses(nextRun);
}
