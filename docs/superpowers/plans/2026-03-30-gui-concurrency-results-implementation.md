# GUI Concurrency And Results UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the run page and results page so the GUI can clearly present multi-chapter concurrent progress, course-level chapter completion state, filtered export controls, and stable file-tree refresh behavior without breaking the current runtime contract.

**Architecture:** Keep the existing backend runtime and export contracts as the primary source of truth, but add one lightweight read API so the results page can reliably fetch course-level latest chapter status even when no `runId` is present in the URL. On the frontend, treat course-level run summary, chapter-level progress, artifact tree state, and export controls as separate view models so concurrent progress and file browsing do not fight over the same UI region.

**Tech Stack:** FastAPI, Pydantic, Next.js, TypeScript, Tailwind CSS, Node test runner, Python `unittest`

---

## File Map

### Backend Read Context

- Modify: `server/app/models/run_session.py`
- Modify: `server/app/application/runs.py`
- Modify: `server/app/api/runs.py`
- Test: `server/tests/test_runs_api.py`

### Run Page

- Modify: `web/components/run/run-session-workbench.tsx`
- Modify: `web/lib/api/runs.ts`
- Test: `web/tests/run-workbench-layout.test.ts`
- Create: `web/tests/run-workbench-chapter-progress.test.ts`

### Results Page

- Modify: `web/components/results/results-workbench.tsx`
- Modify: `web/lib/results-view.ts`
- Modify: `web/lib/results-refresh.ts`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `web/lib/api/runs.ts`
- Test: `web/tests/results-view.test.ts`
- Test: `web/tests/results-refresh.test.ts`
- Modify: `web/tests/results-layout.test.ts`
- Create: `web/tests/results-workbench-state.test.ts`

### Documentation

- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/workstreams/blueprint-runtime.md`
- Modify: `PLANS.md`

---

### Task 1: Add A Course-Level Results Status Read API

**Files:**
- Modify: `server/app/models/run_session.py`
- Modify: `server/app/application/runs.py`
- Modify: `server/app/api/runs.py`
- Test: `server/tests/test_runs_api.py`

- [ ] **Step 1: Write the failing backend tests**

Cover these behaviors:

- results page can fetch the latest chapter-run snapshot by `course_id` without a `runId`
- payload includes:
  - latest run id when one exists
  - latest run status
  - `chapter_progress[]`
  - `stages[]`
- if no eligible chapter run exists, the API returns an empty-but-valid course context instead of 500

- [ ] **Step 2: Run the new backend tests to prove the read API does not exist yet**

Run:
- `python -m unittest server.tests.test_runs_api.RunsApiTests -v`

Expected: FAIL on the new course-level results context tests.

- [ ] **Step 3: Add a lightweight read model for results context**

Implement a small course-level response model instead of overloading artifacts tree:

```python
class CourseResultsContext(BaseModel):
    course_id: str
    latest_run: RunSession | None = None
```

Keep this read-only and do not mix export tree payloads with run status payloads.

- [ ] **Step 4: Implement application lookup for latest chapter run by course**

In `server/app/application/runs.py`, add a method that:

- scans persisted/current run records for the same `course_id`
- prefers the most recent chapter run
- refreshes its runtime-derived fields before returning it

Do not reuse `global` run snapshots as the course-level chapter status source.

- [ ] **Step 5: Expose the API in `server/app/api/runs.py`**

Add a route shaped like:

```python
@router.get("/courses/{course_id}/results-context")
def get_course_results_context(course_id: str): ...
```

The exact path can vary if the repo already has a better local convention, but it must remain:

- course-scoped
- read-only
- stable without `runId`

- [ ] **Step 6: Re-run backend tests**

Run:
- `python -m unittest server.tests.test_runs_api.RunsApiTests -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/app/models/run_session.py server/app/application/runs.py server/app/api/runs.py server/tests/test_runs_api.py
git commit -m "feat: add course results context api"
```

### Task 2: Promote Chapter Progress To The Primary Run Page View

**Files:**
- Modify: `web/components/run/run-session-workbench.tsx`
- Modify: `web/lib/api/runs.ts`
- Test: `web/tests/run-workbench-layout.test.ts`
- Create: `web/tests/run-workbench-chapter-progress.test.ts`

- [ ] **Step 1: Write the failing frontend tests**

Cover these behaviors:

- run page renders a dedicated chapter progress area
- chapter cards show:
  - chapter id
  - status
  - current step
  - completion ratio
  - export-ready signal
- `stages[]` remains visible but is clearly secondary

- [ ] **Step 2: Run the run-page tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts`

Expected: FAIL because the current workbench still uses the serial data rail as the dominant view.

- [ ] **Step 3: Add chapter progress display helpers if needed**

If the component starts getting crowded, extract tiny local helpers such as:

```ts
function getChapterTone(status: string): string
function getChapterProgressLabel(done: number, total: number): string
```

Do not introduce a large abstraction for one screen.

- [ ] **Step 4: Rewrite the run page information hierarchy**

In `web/components/run/run-session-workbench.tsx`:

- keep the top summary card
- add a chapter-progress panel as the main content surface
- demote the existing `stages[]` rail to a course-level summary block
- keep logs and error display as a separate block

Required behavior:

- multiple `running` chapters must be visible simultaneously
- chapter order must remain stable
- `export_ready` should be visually distinguishable from generic `completed`

- [ ] **Step 5: Re-run the run-page tests**

Run:
- `node --experimental-strip-types --test web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/components/run/run-session-workbench.tsx web/lib/api/runs.ts web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts
git commit -m "feat: redesign run page for chapter concurrency"
```

### Task 3: Add Course-Level Chapter Status To The Results Tree

**Files:**
- Modify: `web/components/results/results-workbench.tsx`
- Modify: `web/lib/results-view.ts`
- Modify: `web/lib/api/runs.ts`
- Test: `web/tests/results-view.test.ts`
- Modify: `web/tests/results-layout.test.ts`

- [ ] **Step 1: Write the failing results-tree tests**

Cover these behaviors:

- chapter folders can display:
  - `pending`
  - `running`
  - `completed`
  - `failed`
  - `export_ready`
- results page can show:
  - course-level status context
  - current-run badge when `runId` is present

- [ ] **Step 2: Run the results-tree tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/results-view.test.ts web/tests/results-layout.test.ts`

Expected: FAIL because the current tree model has no chapter-status join or current-run marker.

- [ ] **Step 3: Extend the results tree model in `web/lib/results-view.ts`**

Introduce explicit chapter metadata on chapter folder nodes, for example:

```ts
type ChapterTreeFolderNode = {
  key: string;
  label: string;
  chapterId: string;
  status: string | null;
  exportReady: boolean;
  children: ArtifactTreeNode[];
}
```

Keep file nodes simple. Do not force status metadata onto every leaf file.

- [ ] **Step 4: Join chapter progress into the results tree**

In `results-workbench.tsx`:

- fetch course-level results context
- derive a `chapterProgressById` map
- pass it into the tree builder or a dedicated tree-decoration step

Use course-level latest status as the chapter badge source. Do not infer chapter completion from file presence.

- [ ] **Step 5: Add current-run labeling without rebinding chapter status**

When `runId` exists:

- show a parent-level “当前 run” badge or summary
- do not switch chapter badges to that run if course-level latest context differs

- [ ] **Step 6: Re-run the results-tree tests**

Run:
- `node --experimental-strip-types --test web/tests/results-view.test.ts web/tests/results-layout.test.ts`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/components/results/results-workbench.tsx web/lib/results-view.ts web/lib/api/runs.ts web/tests/results-view.test.ts web/tests/results-layout.test.ts
git commit -m "feat: add chapter status to results tree"
```

### Task 4: Add Filtered Export Controls And Stable Auto-Refresh

**Files:**
- Modify: `web/components/results/results-workbench.tsx`
- Modify: `web/lib/results-refresh.ts`
- Modify: `web/lib/api/artifacts.ts`
- Test: `web/tests/artifacts-api.test.ts`
- Test: `web/tests/results-refresh.test.ts`
- Create: `web/tests/results-workbench-state.test.ts`

- [ ] **Step 1: Write the failing interaction tests**

Cover these behaviors:

- results page exposes:
  - “仅已完成章节”
  - “仅最终产物”
- export link reflects each toggle combination
- artifact refresh preserves:
  - current `expandedKeys`
  - current selected file
- newly arrived folders do not auto-expand unless needed for the selected path

- [ ] **Step 2: Run the interaction tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/artifacts-api.test.ts web/tests/results-refresh.test.ts web/tests/results-workbench-state.test.ts`

Expected: FAIL because the current page only exports the default ZIP and merges all new tree keys into `expandedKeys`.

- [ ] **Step 3: Add explicit export toggle state**

In `results-workbench.tsx`, track two booleans:

```ts
const [completedChaptersOnly, setCompletedChaptersOnly] = useState(false);
const [finalOutputsOnly, setFinalOutputsOnly] = useState(false);
```

Build the export URL via:

```ts
buildExportUrl(courseId, {
  cacheBust: exportCacheBust,
  completedChaptersOnly,
  finalOutputsOnly,
})
```

- [ ] **Step 4: Replace auto-expand-on-refresh with preservation logic**

Refactor refresh handling so that it:

- keeps only still-valid expanded keys
- keeps the selected file when it still exists
- does not auto-add all new folders
- only auto-opens ancestors of the current selected path

If the logic grows, extract a pure helper into `web/lib/results-refresh.ts`.

- [ ] **Step 5: Re-run the interaction tests**

Run:
- `node --experimental-strip-types --test web/tests/artifacts-api.test.ts web/tests/results-refresh.test.ts web/tests/results-workbench-state.test.ts`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/components/results/results-workbench.tsx web/lib/results-refresh.ts web/lib/api/artifacts.ts web/tests/artifacts-api.test.ts web/tests/results-refresh.test.ts web/tests/results-workbench-state.test.ts
git commit -m "feat: add filtered export controls and stable tree refresh"
```

### Task 5: Stabilize Results Layout For Deep Tree Expansion

**Files:**
- Modify: `web/components/results/results-workbench.tsx`
- Modify: `web/tests/results-layout.test.ts`

- [ ] **Step 1: Write the failing layout tests**

Cover these behaviors:

- file tree and preview remain separate columns at large breakpoints
- left tree column is no longer capped at the current narrow `minmax(250px,300px)` contract
- deep tree content does not force the preview panel below the tree

- [ ] **Step 2: Run the layout tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/results-layout.test.ts`

Expected: FAIL because the current layout still uses the old fixed-width grid contract.

- [ ] **Step 3: Adjust the results page grid contract**

Update `results-workbench.tsx` so the left column can breathe without collapsing the right preview.

Concrete target:

- replace the current hard cap grid with a more elastic two-column rule
- keep the tree column independently scrollable
- keep the preview column sticky or height-bounded as needed

Do not introduce a draggable splitter in this batch unless the existing flex/grid approach proves insufficient.

- [ ] **Step 4: Re-run the layout tests**

Run:
- `node --experimental-strip-types --test web/tests/results-layout.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/components/results/results-workbench.tsx web/tests/results-layout.test.ts
git commit -m "fix: stabilize results tree and preview layout"
```

### Task 6: Document The New GUI Baseline And Run Final Verification

**Files:**
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/workstreams/blueprint-runtime.md`
- Modify: `PLANS.md`

- [ ] **Step 1: Update `docs/runbooks/gui-dev.md`**

Document:

- run-page chapter card view
- course-level results tree status
- current-run badge semantics
- filtered export controls
- auto-refresh preserving expand/collapse state

- [ ] **Step 2: Update runtime-facing docs if any GUI/runtime contract language changed**

If the implementation added the new course-level results context API or clarified results-page status source, update:

- `docs/runbooks/run-course.md`
- `docs/workstreams/blueprint-runtime.md`

Keep the wording aligned with actual shipped behavior.

- [ ] **Step 3: Update `PLANS.md`**

Add or mark the GUI concurrency/results UX batch entry so future agents can find:

- the spec
- this implementation plan
- expected validation commands

- [ ] **Step 4: Run focused backend validation**

Run:
- `python -m unittest server.tests.test_runs_api -v`

Expected: PASS

- [ ] **Step 5: Run focused frontend validation**

Run:
- `node --experimental-strip-types --test web/tests/artifacts-api.test.ts web/tests/results-view.test.ts web/tests/results-refresh.test.ts web/tests/results-layout.test.ts web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts web/tests/results-workbench-state.test.ts`

Expected: PASS

- [ ] **Step 6: Run broader GUI validation**

Run:
- `python -m unittest server.tests.test_health server.tests.test_course_drafts_api server.tests.test_templates_api server.tests.test_runs_api server.tests.test_artifacts_api -v`
- `npm run lint`
- `npm run build`

Expected: PASS, or clearly documented environment-specific blocker.

- [ ] **Step 7: Commit**

```bash
git add docs/runbooks/gui-dev.md docs/runbooks/run-course.md docs/workstreams/blueprint-runtime.md PLANS.md
git commit -m "docs: close gui concurrency results ux baseline"
```
