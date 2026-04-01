# Stitch V2 Frontend Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default GUI shell and page presentations with a high-fidelity Stitch V2 interface while preserving all currently shipped draft, config, run, results, empty-state, and preview behaviors.

**Architecture:** Introduce a dedicated Stitch V2 presentation layer that owns layout, visual hierarchy, and shared UI primitives, while reusing the existing backend-facing workbench logic and runtime/API contracts. Migrate page-by-page behind the current routes, keep preview explicitly query-gated, and only switch the default route composition after the parity matrix and smoke flows pass.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Tailwind CSS, Node test runner with `--experimental-strip-types`, existing FastAPI-backed Web APIs

---

## File Map

### Shared V2 Shell And Presentation Layer

- Modify: `web/app/globals.css`
- Modify: `web/components/app-shell.tsx`
- Create: `web/components/stitch-v2/shell-header.tsx`
- Create: `web/components/stitch-v2/shell-sidebar.tsx`
- Create: `web/components/stitch-v2/page-hero.tsx`
- Create: `web/components/stitch-v2/surface-card.tsx`
- Create: `web/components/stitch-v2/status-chip.tsx`
- Create: `web/components/stitch-v2/empty-state-panel.tsx`
- Test: `web/tests/app-shell-branding.test.ts`
- Test: `web/tests/app-shell-state.test.ts`

### Overview And Empty States

- Modify: `web/app/page.tsx`
- Modify: `web/app/runs/page.tsx`
- Modify: `web/app/courses/results/page.tsx`
- Create: `web/components/overview/overview-workbench.tsx`
- Create: `web/tests/overview-workbench.test.ts`

### Input V2

- Modify: `web/app/courses/new/input/page.tsx`
- Modify: `web/components/input/course-draft-workbench.tsx`
- Create: `web/components/input/input-v2-sections.tsx`
- Modify: `web/lib/context-panel.ts`
- Test: `web/tests/input-workbench-ui.test.ts`
- Test: `web/tests/context-panel.test.ts`

### Config V2

- Modify: `web/app/courses/new/config/page.tsx`
- Modify: `web/components/config/template-config-workbench.tsx`
- Modify: `web/lib/config-workbench-view.ts`
- Create: `web/components/config/config-v2-sections.tsx`
- Test: `web/tests/config-workbench-view.test.ts`
- Test: `web/tests/config-workbench-ui.test.ts`

### Run V2

- Modify: `web/app/runs/[runId]/page.tsx`
- Modify: `web/components/run/run-session-workbench.tsx`
- Create: `web/components/run/run-v2-sections.tsx`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/run-workbench-layout.test.ts`
- Test: `web/tests/run-workbench-chapter-progress.test.ts`
- Test: `web/tests/preview-mode.test.ts`

### Results V2

- Modify: `web/app/courses/[courseId]/results/page.tsx`
- Modify: `web/components/results/results-workbench.tsx`
- Create: `web/components/results/results-v2-sections.tsx`
- Modify: `web/lib/results-view.ts`
- Modify: `web/lib/results-refresh.ts`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/results-layout.test.ts`
- Test: `web/tests/results-workbench-state.test.ts`
- Test: `web/tests/results-refresh.test.ts`
- Test: `web/tests/results-view.test.ts`
- Test: `web/tests/results-tree-chapter-status.test.ts`
- Test: `web/tests/results-interaction.test.ts`

### Route Cutover / Regression / Documentation

- Modify: `web/lib/app-shell-state.ts`
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/README.md`
- Modify: `PLANS.md`

---

### Task 1: Build The Shared Stitch V2 Design Foundation

**Files:**
- Modify: `web/app/globals.css`
- Modify: `web/components/app-shell.tsx`
- Create: `web/components/stitch-v2/shell-header.tsx`
- Create: `web/components/stitch-v2/shell-sidebar.tsx`
- Create: `web/components/stitch-v2/page-hero.tsx`
- Create: `web/components/stitch-v2/surface-card.tsx`
- Create: `web/components/stitch-v2/status-chip.tsx`
- Create: `web/components/stitch-v2/empty-state-panel.tsx`
- Test: `web/tests/app-shell-branding.test.ts`
- Test: `web/tests/app-shell-state.test.ts`

- [ ] **Step 1: Extend the failing shell/design tests**

Add assertions for:

- Stitch V2 visual tokens in `globals.css`
- a distinct V2 shell header / sidebar structure
- shared card and badge primitives existing as dedicated files
- current four-step product nav still present in the shell

- [ ] **Step 2: Run the shell/design tests to confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-branding.test.ts web/tests/app-shell-state.test.ts`

Expected: FAIL because the current shell is still a single monolithic frame with no dedicated V2 primitives.

- [ ] **Step 3: Add shared Stitch V2 primitives**

Create focused presentational components with one responsibility each:

- `shell-header.tsx`
- `shell-sidebar.tsx`
- `page-hero.tsx`
- `surface-card.tsx`
- `status-chip.tsx`
- `empty-state-panel.tsx`

Keep them stateless and presentation-only.

- [ ] **Step 4: Move Stitch V2 tokens into shared styling**

In `web/app/globals.css`:

- define CSS variables for the main surface hierarchy
- define typography utility classes if needed
- define shared backdrop / surface / shadow / rounded treatments

Do not introduce a new CSS framework or theme runtime.

- [ ] **Step 5: Refactor `app-shell.tsx` to consume the new shared primitives**

Required behavior:

- keep the existing product navigation model
- keep the right-side context rail
- adopt the Stitch V2 shell structure and visual hierarchy
- do not change route semantics while changing the shell layout

- [ ] **Step 6: Re-run the shell/design tests**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-branding.test.ts web/tests/app-shell-state.test.ts`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/app/globals.css web/components/app-shell.tsx web/components/stitch-v2 web/tests/app-shell-branding.test.ts web/tests/app-shell-state.test.ts
git commit -m "feat: add stitch v2 shell foundation"
```

### Task 2: Migrate Overview And Product Empty States

**Files:**
- Modify: `web/app/page.tsx`
- Modify: `web/app/runs/page.tsx`
- Modify: `web/app/courses/results/page.tsx`
- Create: `web/components/overview/overview-workbench.tsx`
- Test: `web/tests/app-shell-state.test.ts`
- Create: `web/tests/overview-workbench.test.ts`
- Test: `web/tests/preview-mode.test.ts`

- [ ] **Step 1: Write failing tests for the overview and empty-state V2 layout**

Cover:

- home page uses a dedicated overview workbench
- `/runs` renders a product empty state, not preview
- `/courses/results` renders a product empty state, not preview
- empty states clearly distinguish product flow from internal preview mode

- [ ] **Step 2: Run the tests to confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts web/tests/overview-workbench.test.ts`

Expected: FAIL because the current pages still use lightweight placeholders and the overview has not been rebuilt around Stitch V2.

- [ ] **Step 3: Create `overview-workbench.tsx`**

Implement the V2 overview as a real component so the home page does not remain a one-off template.

It must:

- use the shared Stitch V2 shell primitives
- keep the four-step product flow visible
- avoid fake product actions with no real meaning

- [ ] **Step 4: Upgrade `/runs` and `/courses/results` empty states**

Use `empty-state-panel.tsx` so both product empty routes:

- feel like first-class pages
- retain `draftId` / `courseId` context where available
- clearly state they are product empty states, not preview

- [ ] **Step 5: Re-run the overview/empty-state tests**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts web/tests/overview-workbench.test.ts`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/app/page.tsx web/app/runs/page.tsx web/app/courses/results/page.tsx web/components/overview/overview-workbench.tsx web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts web/tests/overview-workbench.test.ts
git commit -m "feat: migrate overview and empty states to stitch v2"
```

### Task 3: Rebuild The Input Page In Stitch V2 While Preserving Local-Material Flow

**Files:**
- Modify: `web/app/courses/new/input/page.tsx`
- Modify: `web/components/input/course-draft-workbench.tsx`
- Create: `web/components/input/input-v2-sections.tsx`
- Modify: `web/lib/context-panel.ts`
- Test: `web/tests/input-workbench-ui.test.ts`
- Test: `web/tests/context-panel.test.ts`

- [ ] **Step 1: Write failing input-page tests**

Cover:

- the input page uses dedicated V2 section composition
- subtitle upload, manual subtitle assets, and draft summary remain visible
- course-link UI remains absent
- context panel still reflects the current draft/runtime fields

- [ ] **Step 2: Run the input-page tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/input-workbench-ui.test.ts web/tests/context-panel.test.ts`

Expected: FAIL because the current input page is still laid out as the older workbench structure.

- [ ] **Step 3: Extract input V2 presentation sections**

Create `input-v2-sections.tsx` to host:

- hero / title region
- local file upload surface
- manual transcript asset editor surface
- coming-soon modality cards
- draft summary presentation

Keep submission logic in `course-draft-workbench.tsx`.

- [ ] **Step 4: Refactor `course-draft-workbench.tsx` to use the V2 sections**

Required behavior:

- preserve local file upload flow
- preserve manual subtitle asset authoring
- preserve draft creation and routing to config
- preserve the no-course-link product decision

- [ ] **Step 5: Re-run the input-page tests**

Run:
- `node --experimental-strip-types --test web/tests/input-workbench-ui.test.ts web/tests/context-panel.test.ts`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/app/courses/new/input/page.tsx web/components/input/course-draft-workbench.tsx web/components/input/input-v2-sections.tsx web/lib/context-panel.ts web/tests/input-workbench-ui.test.ts web/tests/context-panel.test.ts
git commit -m "feat: migrate input page to stitch v2"
```

### Task 4: Rebuild The Config Page In Stitch V2 Without Restoring Hidden Controls

**Files:**
- Modify: `web/app/courses/new/config/page.tsx`
- Modify: `web/components/config/template-config-workbench.tsx`
- Modify: `web/lib/config-workbench-view.ts`
- Create: `web/components/config/config-v2-sections.tsx`
- Test: `web/tests/config-workbench-view.test.ts`
- Test: `web/tests/config-workbench-ui.test.ts`

- [ ] **Step 1: Write failing config-page tests**

Cover:

- config page uses a dedicated V2 section composition
- template controls remain present
- AI service configuration remains collapsed by default
- course-level runtime override controls remain hidden
- start/continue run and update-global actions remain visible

- [ ] **Step 2: Run the config tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/config-workbench-view.test.ts web/tests/config-workbench-ui.test.ts`

Expected: FAIL because the page is still rendered through the older workbench layout.

- [ ] **Step 3: Extract config V2 presentation sections**

Create `config-v2-sections.tsx` to host:

- template chooser / parameter editor shell
- AI service configuration shell
- run controls shell
- output summary shell

Keep all real save/start handlers in `template-config-workbench.tsx`.

- [ ] **Step 4: Refactor `template-config-workbench.tsx` to use the V2 sections**

Required behavior:

- preserve template selection and saved config semantics
- preserve AI service save behavior
- preserve run start and global update actions
- continue to hide course-level runtime override UI

- [ ] **Step 5: Re-run the config tests**

Run:
- `node --experimental-strip-types --test web/tests/config-workbench-view.test.ts web/tests/config-workbench-ui.test.ts`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/app/courses/new/config/page.tsx web/components/config/template-config-workbench.tsx web/components/config/config-v2-sections.tsx web/lib/config-workbench-view.ts web/tests/config-workbench-view.test.ts web/tests/config-workbench-ui.test.ts
git commit -m "feat: migrate config page to stitch v2"
```

### Task 5: Rebuild The Run Page In Stitch V2 And Preserve Runtime Semantics

**Files:**
- Modify: `web/app/runs/[runId]/page.tsx`
- Modify: `web/components/run/run-session-workbench.tsx`
- Create: `web/components/run/run-v2-sections.tsx`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/run-workbench-layout.test.ts`
- Test: `web/tests/run-workbench-chapter-progress.test.ts`
- Test: `web/tests/preview-mode.test.ts`

- [ ] **Step 1: Write failing run-page migration tests**

Cover:

- run page renders through dedicated V2 sections
- run summary, chapter cards, runtime flow, logs, and actions all remain present
- preview still requires explicit `mode=preview`
- `/runs` empty route and `/runs/[runId]` real route stay distinct

- [ ] **Step 2: Run the run-page tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts web/tests/preview-mode.test.ts`

Expected: FAIL because the run page is still the earlier visual structure.

- [ ] **Step 3: Extract run V2 presentation sections**

Create `run-v2-sections.tsx` to host:

- run summary hero
- chapter concurrency board
- runtime flow panel
- log/error panel

Keep the real state machine, SSE subscriptions, resume, clean, and preview gating in `run-session-workbench.tsx`.

- [ ] **Step 4: Refactor `run-session-workbench.tsx` to use V2 sections**

Required behavior:

- preserve `Resume` / `Clean` action rules
- preserve SSE updates
- preserve chapter order and export-ready emphasis
- preserve preview-only behavior

- [ ] **Step 5: Re-run the run-page tests**

Run:
- `node --experimental-strip-types --test web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts web/tests/preview-mode.test.ts`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/app/runs/[runId]/page.tsx web/components/run/run-session-workbench.tsx web/components/run/run-v2-sections.tsx web/lib/api/runs.ts web/lib/preview/workbench.ts web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts web/tests/preview-mode.test.ts
git commit -m "feat: migrate run page to stitch v2"
```

### Task 6: Rebuild The Results Page In Stitch V2 And Preserve Course-Level Status Semantics

**Files:**
- Modify: `web/app/courses/[courseId]/results/page.tsx`
- Modify: `web/components/results/results-workbench.tsx`
- Create: `web/components/results/results-v2-sections.tsx`
- Modify: `web/lib/results-view.ts`
- Modify: `web/lib/results-refresh.ts`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/results-layout.test.ts`
- Test: `web/tests/results-workbench-state.test.ts`
- Test: `web/tests/results-refresh.test.ts`
- Test: `web/tests/results-view.test.ts`
- Test: `web/tests/results-tree-chapter-status.test.ts`
- Test: `web/tests/results-interaction.test.ts`

- [ ] **Step 1: Write failing results-page migration tests**

Cover:

- results page renders through dedicated V2 sections
- file tree, preview pane, reviewer/export pane all remain present
- course-level latest-run semantics remain intact
- scoped run is still label-only
- export filters and tree refresh behavior remain intact

- [ ] **Step 2: Run the results-page tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/results-layout.test.ts web/tests/results-workbench-state.test.ts web/tests/results-refresh.test.ts web/tests/results-view.test.ts web/tests/results-tree-chapter-status.test.ts web/tests/results-interaction.test.ts`

Expected: FAIL because the page is still rendered through the prior layout.

- [ ] **Step 3: Extract results V2 presentation sections**

Create `results-v2-sections.tsx` to host:

- file-tree column shell
- preview column shell
- review/export shell
- course/scoped status headers

Keep real loading, SSE refresh, export toggle state, and file selection state in `results-workbench.tsx`.

- [ ] **Step 4: Refactor `results-workbench.tsx` to use V2 sections**

Required behavior:

- preserve course-level chapter status source
- preserve scoped run label-only semantics
- preserve export toggle semantics
- preserve tree refresh and selection stability
- preserve preview-only mode

- [ ] **Step 5: Re-run the results-page tests**

Run:
- `node --experimental-strip-types --test web/tests/results-layout.test.ts web/tests/results-workbench-state.test.ts web/tests/results-refresh.test.ts web/tests/results-view.test.ts web/tests/results-tree-chapter-status.test.ts web/tests/results-interaction.test.ts`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/app/courses/[courseId]/results/page.tsx web/components/results/results-workbench.tsx web/components/results/results-v2-sections.tsx web/lib/results-view.ts web/lib/results-refresh.ts web/lib/api/artifacts.ts web/lib/api/runs.ts web/lib/preview/workbench.ts web/tests/results-layout.test.ts web/tests/results-workbench-state.test.ts web/tests/results-refresh.test.ts web/tests/results-view.test.ts web/tests/results-tree-chapter-status.test.ts web/tests/results-interaction.test.ts
git commit -m "feat: migrate results page to stitch v2"
```

### Task 7: Cut Default Product Routes Over To Stitch V2 And Remove Transitional UI Debt

**Files:**
- Modify: `web/components/app-shell.tsx`
- Modify: `web/lib/app-shell-state.ts`
- Modify: `web/app/page.tsx`
- Modify: `web/app/courses/new/input/page.tsx`
- Modify: `web/app/courses/new/config/page.tsx`
- Modify: `web/app/runs/page.tsx`
- Modify: `web/app/runs/[runId]/page.tsx`
- Modify: `web/app/courses/results/page.tsx`
- Modify: `web/app/courses/[courseId]/results/page.tsx`
- Test: `web/tests/app-shell-state.test.ts`
- Test: `web/tests/preview-mode.test.ts`

- [ ] **Step 1: Write a failing cutover test set**

Cover:

- default product routes all resolve to V2 composition
- preview routes remain explicit and internal
- no product navigation invents preview ids or preview semantics
- the parity matrix release gate is expressible in the test set comments and checkpoints

- [ ] **Step 2: Run the cutover tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts`

Expected: FAIL until all route composition and route-state assumptions are aligned with the final V2 structure.

- [ ] **Step 3: Remove or isolate obsolete transitional shell logic**

Clean up temporary V1-only layout fragments or duplicated route composition logic left over from migration.

Do not delete anything until the route tests and smoke validations pass.

- [ ] **Step 4: Align all product routes with the final V2 composition**

Required final behavior:

- `/`, `/courses/new/input`, `/courses/new/config`, `/runs`, `/runs/[runId]`, `/courses/results`, `/courses/[courseId]/results` all use the V2 shell and page sections
- `preview` remains explicit and internal-only

- [ ] **Step 5: Run the release-gate smoke validation**

Run at least:
- `node --experimental-strip-types --test web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts web/tests/input-workbench-ui.test.ts web/tests/config-workbench-ui.test.ts web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts web/tests/results-layout.test.ts web/tests/results-workbench-state.test.ts web/tests/results-refresh.test.ts web/tests/results-view.test.ts web/tests/results-tree-chapter-status.test.ts web/tests/results-interaction.test.ts`
- `npm run lint`
- `npm run build`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/components/app-shell.tsx web/lib/app-shell-state.ts web/app/page.tsx web/app/courses/new/input/page.tsx web/app/courses/new/config/page.tsx web/app/runs/page.tsx web/app/runs/[runId]/page.tsx web/app/courses/results/page.tsx web/app/courses/[courseId]/results/page.tsx web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts
git commit -m "feat: switch product routes to stitch v2"
```

### Task 8: Update Documentation, PLANS, And Final Validation

**Files:**
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/README.md`
- Modify: `PLANS.md`

- [ ] **Step 1: Write the failing documentation checklist**

Create a short checklist in the task notes and confirm the docs are currently missing:

- Stitch V2 as the default product shell
- preview remains internal-only
- `/runs` and `/courses/results` are product empty-state routes
- the new release gate validation set

- [ ] **Step 2: Update the docs**

Required updates:

- `docs/runbooks/gui-dev.md`
  - explain Stitch V2 default product pages
  - explain preview boundary
  - explain product empty-state routes
- `docs/README.md`
  - refresh the current GUI baseline if the default product shell has materially changed
- `PLANS.md`
  - add a new batch index entry for the Stitch V2 migration
  - include goal, scope, execution batches, and validation references

- [ ] **Step 3: Run the final validation suite**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-branding.test.ts web/tests/app-shell-state.test.ts web/tests/overview-workbench.test.ts web/tests/input-workbench-ui.test.ts web/tests/config-workbench-view.test.ts web/tests/config-workbench-ui.test.ts web/tests/context-panel.test.ts web/tests/preview-mode.test.ts web/tests/results-layout.test.ts web/tests/results-workbench-state.test.ts web/tests/results-refresh.test.ts web/tests/results-view.test.ts web/tests/results-tree-chapter-status.test.ts web/tests/results-interaction.test.ts web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts`
- `npm run lint`
- `npm run build`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/runbooks/gui-dev.md docs/README.md PLANS.md
git commit -m "docs: finalize stitch v2 migration plan references"
```

## Notes For Execution

- Stay inside the frozen-contract boundaries from the spec.
- Prefer creating presentational section components over inflating the existing workbench files further.
- Keep preview routing explicit: no product navigation should rely on `preview-run`, `preview-course`, or similar pseudo-identities.
- When a task creates a new V2 section component, keep it presentation-only and leave API wiring in the workbench unless the plan explicitly says otherwise.
- If a task requires changing semantics instead of presentation, stop and update the spec before proceeding.
