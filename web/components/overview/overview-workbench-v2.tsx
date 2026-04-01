import { AppShell } from "@/components/app-shell";
import { OverviewV2Sections } from "@/components/overview/overview-v2-sections";
import { AppShellState, buildAppShellState } from "@/lib/app-shell-state";

export function OverviewWorkbenchV2({
  shellState = buildAppShellState("/", new URLSearchParams()),
}: {
  shellState?: AppShellState;
}) {
  return (
    <AppShell eyebrow="Overview" title="Course Production Workbench" shellState={shellState}>
      <OverviewV2Sections shellState={shellState} />
    </AppShell>
  );
}
