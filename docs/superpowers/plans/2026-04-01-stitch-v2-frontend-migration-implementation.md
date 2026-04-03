# Stitch V2 Frontend Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default GUI shell and page presentations with a high-fidelity Stitch V2 interface while preserving all currently shipped draft, config, run, results, empty-state, and preview behaviors.

**Architecture:** Introduce a dedicated Stitch V2 presentation layer that owns layout, visual hierarchy, and shared UI primitives, while reusing the existing backend-facing workbench logic and runtime/API contracts. Build the V2 page compositions in parallel first, keep current default routes on the existing workbenches until the cutover batch, keep preview explicitly query-gated, and only switch the default route composition after the parity matrix and smoke flows pass.

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

- Create: `web/components/overview/overview-workbench-v2.tsx`
- Create: `web/components/empty/run-empty-state-v2.tsx`
- Create: `web/components/empty/results-empty-state-v2.tsx`
- Create: `web/tests/overview-v2-workbench.test.ts`

### Input V2

- Create: `web/components/input/course-draft-workbench-v2.tsx`
- Create: `web/components/input/input-v2-sections.tsx`
- Test: `web/tests/input-v2-workbench.test.ts`

### Config V2

- Create: `web/components/config/template-config-workbench-v2.tsx`
- Create: `web/components/config/config-v2-sections.tsx`
- Test: `web/tests/config-v2-workbench.test.ts`

### Run V2

- Create: `web/components/run/run-session-workbench-v2.tsx`
- Create: `web/components/run/run-v2-sections.tsx`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/run-v2-workbench.test.ts`
- Test: `web/tests/preview-mode.test.ts`

### Results V2

- Create: `web/components/results/results-workbench-v2.tsx`
- Create: `web/components/results/results-v2-sections.tsx`
- Modify: `web/lib/results-view.ts`
- Modify: `web/lib/results-refresh.ts`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/results-v2-workbench.test.ts`
- Test: `web/tests/artifacts-api.test.ts`

### Route Cutover / Regression / Documentation

- Modify: `web/app/page.tsx`
- Modify: `web/app/courses/new/input/page.tsx`
- Modify: `web/app/courses/new/config/page.tsx`
- Modify: `web/app/runs/page.tsx`
- Modify: `web/app/runs/[runId]/page.tsx`
- Modify: `web/app/courses/results/page.tsx`
- Modify: `web/app/courses/[courseId]/results/page.tsx`
- Modify: `web/lib/app-shell-state.ts`
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/README.md`
- Modify: `PLANS.md`

---

## Reference Assets Root

All high-fidelity visual work must reference the local Stitch exports at:

- `out/stitch/14050487305097227160/`

Each task below binds its own `.png` and `.html` asset pair. Do not implement “generic Stitch style” from memory when the exported reference files exist locally.

## Dual-Track Execution Rule

Tasks 2-6 are **parallel V2 build tasks**, not product-route cutover tasks.

Rules:

- Tasks 2-6 may create new `*-v2.tsx` workbenches and presentation sections.
- Tasks 2-6 may refactor shared helpers only when current default routes remain behaviorally unchanged.
- Tasks 2-6 must **not** replace the default imports in `web/app/` route files.
- Task 7 is the **first** batch allowed to switch default product routes to the V2 workbenches.
- If a task needs to change default route behavior before Task 7, stop and update the spec/plan first.

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

**Reference Assets:**
- `out/stitch/14050487305097227160/overview-v2-72223e80f4fc44f496faa80b5192e38f.png`
- `out/stitch/14050487305097227160/overview-v2-72223e80f4fc44f496faa80b5192e38f.html`
- `out/stitch/14050487305097227160/input-step1-v2-98412b91e37f42b78f70404496d85538.png`
- `out/stitch/14050487305097227160/config-step2-v2-925e1adc724a4e948f7aff858c71d329.png`
- `out/stitch/14050487305097227160/run-step3-v2-2732c03d32c84715a16587ceed205b9b.png`
- `out/stitch/14050487305097227160/results-step4-v2-4d882ed4de034a6aa99c5bfe1123da05.png`

- [ ] **Step 1: Review the shared visual reference assets**

Open the local Stitch exports listed above and note the common shell traits:

- top app bar
- left navigation
- hero spacing
- surface hierarchy
- dark control rail treatment

- [ ] **Step 2: Extend the failing shell/design tests**

Add assertions for:

- Stitch V2 visual tokens in `globals.css`
- a distinct V2 shell header / sidebar structure
- shared card and badge primitives existing as dedicated files
- current four-step product nav still present in the shell

- [ ] **Step 3: Run the shell/design tests to confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-branding.test.ts web/tests/app-shell-state.test.ts`

Expected: FAIL because the current shell is still a single monolithic frame with no dedicated V2 primitives.

- [ ] **Step 4: Add shared Stitch V2 primitives**

Create focused presentational components with one responsibility each:

- `shell-header.tsx`
- `shell-sidebar.tsx`
- `page-hero.tsx`
- `surface-card.tsx`
- `status-chip.tsx`
- `empty-state-panel.tsx`

Keep them stateless and presentation-only.

- [ ] **Step 5: Move Stitch V2 tokens into shared styling**

In `web/app/globals.css`:

- define CSS variables for the main surface hierarchy
- define typography utility classes if needed
- define shared backdrop / surface / shadow / rounded treatments

Do not introduce a new CSS framework or theme runtime.

- [ ] **Step 6: Refactor `app-shell.tsx` to consume the new shared primitives**

Required behavior:

- keep the existing product navigation model
- keep the right-side context rail
- adopt the Stitch V2 shell structure and visual hierarchy
- do not change route semantics while changing the shell layout

- [ ] **Step 7: Re-run the shell/design tests**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-branding.test.ts web/tests/app-shell-state.test.ts`

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add web/app/globals.css web/components/app-shell.tsx web/components/stitch-v2 web/tests/app-shell-branding.test.ts web/tests/app-shell-state.test.ts
git commit -m "feat: add stitch v2 shell foundation"
```

### Task 2: Migrate Overview And Product Empty States

**Files:**
- Create: `web/components/overview/overview-workbench-v2.tsx`
- Create: `web/components/empty/run-empty-state-v2.tsx`
- Create: `web/components/empty/results-empty-state-v2.tsx`
- Test: `web/tests/app-shell-state.test.ts`
- Create: `web/tests/overview-v2-workbench.test.ts`
- Test: `web/tests/preview-mode.test.ts`

**Reference Assets:**
- `out/stitch/14050487305097227160/overview-v2-72223e80f4fc44f496faa80b5192e38f.png`
- `out/stitch/14050487305097227160/overview-v2-72223e80f4fc44f496faa80b5192e38f.html`

- [ ] **Step 1: Review the overview reference assets**

Inspect the overview `.png` and `.html` and write down:

- hero composition
- CTA grouping
- secondary information density
- how the shell frame presents the workspace

- [ ] **Step 2: Write failing tests for the overview and empty-state V2 layout**

Cover:

- home page uses a dedicated overview workbench
- `/runs` renders a product empty state, not preview
- `/courses/results` renders a product empty state, not preview
- empty states clearly distinguish product flow from internal preview mode

- [ ] **Step 3: Run the tests to confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts web/tests/overview-v2-workbench.test.ts`

Expected: FAIL because the current pages still use lightweight placeholders and the overview has not been rebuilt around Stitch V2.

- [ ] **Step 4: Create `overview-workbench-v2.tsx`**

Implement the V2 overview as a real component so the home page does not remain a one-off template.

It must:

- use the shared Stitch V2 shell primitives
- keep the four-step product flow visible
- avoid fake product actions with no real meaning

- [ ] **Step 5: Create V2 product empty-state components**

Use `empty-state-panel.tsx` so the V2 empty-state components:

- feel like first-class pages
- retain `draftId` / `courseId` context where available
- clearly state they are product empty states, not preview

Do not wire them into `web/app/` routes yet.

- [ ] **Step 6: Re-run the overview/empty-state tests**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts web/tests/overview-v2-workbench.test.ts`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/components/overview/overview-workbench-v2.tsx web/components/empty/run-empty-state-v2.tsx web/components/empty/results-empty-state-v2.tsx web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts web/tests/overview-v2-workbench.test.ts
git commit -m "feat: build stitch v2 overview and empty states"
```

### Task 3: Rebuild The Input Page In Stitch V2 While Preserving Local-Material Flow

**Files:**
- Create: `web/components/input/course-draft-workbench-v2.tsx`
- Create: `web/components/input/input-v2-sections.tsx`
- Test: `web/tests/input-v2-workbench.test.ts`

**Reference Assets:**
- `out/stitch/14050487305097227160/input-step1-v2-98412b91e37f42b78f70404496d85538.png`
- `out/stitch/14050487305097227160/input-step1-v2-98412b91e37f42b78f70404496d85538.html`

- [ ] **Step 1: Review the input-page reference assets**

Inspect the input `.png` and `.html` and note:

- hero / upload relationship
- supporting “coming soon” surfaces
- how summary information is visually separated from the authoring surface

- [ ] **Step 2: Write failing input-page tests**

Cover:

- the V2 input workbench uses dedicated section composition
- subtitle upload, manual subtitle assets, and draft summary remain visible
- course-link UI remains absent
- the V2 workbench can later replace the default input route without changing semantics

- [ ] **Step 3: Run the input-page tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/input-v2-workbench.test.ts`

Expected: FAIL because the V2 input workbench does not exist yet.

- [ ] **Step 4: Extract input V2 presentation sections**

Create `input-v2-sections.tsx` to host:

- hero / title region
- local file upload surface
- manual transcript asset editor surface
- coming-soon modality cards
- draft summary presentation

Keep real submission and draft state wiring accessible to the V2 workbench. Do not switch the default route import yet.

- [ ] **Step 5: Create `course-draft-workbench-v2.tsx`**

Required behavior:

- preserve local file upload flow
- preserve manual subtitle asset authoring
- preserve draft creation and routing to config
- preserve the no-course-link product decision
- do not replace `web/app/courses/new/input/page.tsx` yet

- [ ] **Step 6: Re-run the input-page tests**

Run:
- `node --experimental-strip-types --test web/tests/input-v2-workbench.test.ts`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/components/input/course-draft-workbench-v2.tsx web/components/input/input-v2-sections.tsx web/tests/input-v2-workbench.test.ts
git commit -m "feat: build stitch v2 input workbench"
```

### Task 4: Rebuild The Config Page In Stitch V2 Without Restoring Hidden Controls

**Files:**
- Create: `web/components/config/template-config-workbench-v2.tsx`
- Create: `web/components/config/config-v2-sections.tsx`
- Test: `web/tests/config-v2-workbench.test.ts`

**Reference Assets:**
- `out/stitch/14050487305097227160/config-step2-v2-925e1adc724a4e948f7aff858c71d329.png`
- `out/stitch/14050487305097227160/config-step2-v2-925e1adc724a4e948f7aff858c71d329.html`

- [ ] **Step 1: Review the config-page reference assets**

Inspect the config `.png` and `.html` and note:

- hero / control surface proportions
- summary rail composition
- what should be primary vs collapsed

- [ ] **Step 2: Write failing config-page tests**

Cover:

- config V2 workbench uses a dedicated section composition
- template controls remain present
- AI service configuration remains collapsed by default
- course-level runtime override controls remain hidden
- start/continue run and update-global actions remain visible

- [ ] **Step 3: Run the config tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/config-v2-workbench.test.ts`

Expected: FAIL because the V2 config workbench does not exist yet.

- [ ] **Step 4: Extract config V2 presentation sections**

Create `config-v2-sections.tsx` to host:

- template chooser / parameter editor shell
- AI service configuration shell
- run controls shell
- output summary shell

Keep all real save/start handlers accessible to the V2 workbench. Do not switch the default route import yet.

- [ ] **Step 5: Create `template-config-workbench-v2.tsx`**

Required behavior:

- preserve template selection and saved config semantics
- preserve AI service save behavior
- preserve run start and global update actions
- continue to hide course-level runtime override UI
- do not replace `web/app/courses/new/config/page.tsx` yet

- [ ] **Step 6: Re-run the config tests**

Run:
- `node --experimental-strip-types --test web/tests/config-v2-workbench.test.ts`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/components/config/template-config-workbench-v2.tsx web/components/config/config-v2-sections.tsx web/tests/config-v2-workbench.test.ts
git commit -m "feat: build stitch v2 config workbench"
```

### Task 5: Rebuild The Run Page In Stitch V2 And Preserve Runtime Semantics

**Files:**
- Create: `web/components/run/run-session-workbench-v2.tsx`
- Create: `web/components/run/run-v2-sections.tsx`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/run-v2-workbench.test.ts`
- Test: `web/tests/preview-mode.test.ts`

**Reference Assets:**
- `out/stitch/14050487305097227160/run-step3-v2-2732c03d32c84715a16587ceed205b9b.png`
- `out/stitch/14050487305097227160/run-step3-v2-2732c03d32c84715a16587ceed205b9b.html`

- [ ] **Step 1: Review the run-page reference assets**

Inspect the run `.png` and `.html` and note:

- top-level monitoring hierarchy
- chapter board visual treatment
- secondary flow/log panel structure

- [ ] **Step 2: Write failing run-page migration tests**

Cover:

- run V2 workbench renders through dedicated V2 sections
- run summary, chapter cards, runtime flow, logs, and actions all remain present
- preview still requires explicit `mode=preview`
- `/runs` empty route and `/runs/[runId]` real route stay distinct

- [ ] **Step 3: Run the run-page tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/run-v2-workbench.test.ts web/tests/preview-mode.test.ts`

Expected: FAIL because the V2 run workbench does not exist yet.

- [ ] **Step 4: Extract run V2 presentation sections**

Create `run-v2-sections.tsx` to host:

- run summary hero
- chapter concurrency board
- runtime flow panel
- log/error panel

Keep the real state machine, SSE subscriptions, resume, clean, and preview gating accessible to the V2 workbench. Do not switch the default route import yet.

- [ ] **Step 5: Create `run-session-workbench-v2.tsx`**

Required behavior:

- preserve `Resume` / `Clean` action rules
- preserve SSE updates
- preserve chapter order and export-ready emphasis
- preserve preview-only behavior
- do not replace `web/app/runs/[runId]/page.tsx` yet

- [ ] **Step 6: Re-run the run-page tests**

Run:
- `node --experimental-strip-types --test web/tests/run-v2-workbench.test.ts web/tests/preview-mode.test.ts`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/components/run/run-session-workbench-v2.tsx web/components/run/run-v2-sections.tsx web/lib/api/runs.ts web/lib/preview/workbench.ts web/tests/run-v2-workbench.test.ts web/tests/preview-mode.test.ts
git commit -m "feat: build stitch v2 run workbench"
```

### Task 6: Rebuild The Results Page In Stitch V2 And Preserve Course-Level Status Semantics

**Files:**
- Create: `web/components/results/results-workbench-v2.tsx`
- Create: `web/components/results/results-v2-sections.tsx`
- Modify: `web/lib/results-view.ts`
- Modify: `web/lib/results-refresh.ts`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/results-v2-workbench.test.ts`
- Test: `web/tests/artifacts-api.test.ts`

**Reference Assets:**
- `out/stitch/14050487305097227160/results-step4-v2-4d882ed4de034a6aa99c5bfe1123da05.png`
- `out/stitch/14050487305097227160/results-step4-v2-4d882ed4de034a6aa99c5bfe1123da05.html`

- [ ] **Step 1: Review the results-page reference assets**

Inspect the results `.png` and `.html` and note:

- file tree / preview / export panel proportions
- course status header treatment
- deep-tree reading rhythm and dark/light surface balance

- [ ] **Step 2: Write failing results-page migration tests**

Cover:

- results V2 workbench renders through dedicated V2 sections
- file tree, preview pane, reviewer/export pane all remain present
- course-level latest-run semantics remain intact
- scoped run is still label-only
- export filters and tree refresh behavior remain intact
- artifacts API helper behavior remains unchanged

- [ ] **Step 3: Run the results-page tests and confirm failure**

Run:
- `node --experimental-strip-types --test web/tests/results-v2-workbench.test.ts web/tests/artifacts-api.test.ts`

Expected: FAIL because the V2 results workbench does not exist yet.

- [ ] **Step 4: Extract results V2 presentation sections**

Create `results-v2-sections.tsx` to host:

- file-tree column shell
- preview column shell
- review/export shell
- course/scoped status headers

Keep real loading, SSE refresh, export toggle state, and file selection state accessible to the V2 workbench. Do not switch the default route import yet.

- [ ] **Step 5: Create `results-workbench-v2.tsx`**

Required behavior:

- preserve course-level chapter status source
- preserve scoped run label-only semantics
- preserve export toggle semantics
- preserve tree refresh and selection stability
- preserve preview-only mode
- do not replace `web/app/courses/[courseId]/results/page.tsx` yet

- [ ] **Step 6: Re-run the results-page tests**

Run:
- `node --experimental-strip-types --test web/tests/results-v2-workbench.test.ts web/tests/artifacts-api.test.ts`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/components/results/results-workbench-v2.tsx web/components/results/results-v2-sections.tsx web/lib/results-view.ts web/lib/results-refresh.ts web/lib/api/artifacts.ts web/lib/api/runs.ts web/lib/preview/workbench.ts web/tests/results-v2-workbench.test.ts web/tests/artifacts-api.test.ts
git commit -m "feat: build stitch v2 results workbench"
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
- Test: `web/tests/artifacts-api.test.ts`

- [ ] **Step 1: Write a failing cutover test set**

Cover:

- default product routes all resolve to V2 composition
- preview routes remain explicit and internal
- no product navigation invents preview ids or preview semantics
- the parity matrix release gate is expressible in the test set comments and checkpoints
- the route files now import the V2 workbenches instead of the old ones

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

- [ ] **Step 5: Run the explicit browser smoke flows from the GUI runbook**

Follow `docs/runbooks/gui-dev.md`:

1. Start services and pass health checks.
2. Product main-flow smoke:
   - `Input -> Config -> Run -> Results`
3. Run control smoke:
   - open a real run
   - execute `resume` or `clean`
   - verify status/log behavior
4. Results semantics smoke:
   - verify course-level latest state
   - verify scoped run label
   - verify filtered export toggles
5. Internal preview smoke:
   - open `/runs/preview?mode=preview&scenario=running`
   - open `/courses/preview/results?mode=preview&scenario=completed`

Record pass/fail bullets in the task handoff for each smoke flow before committing.

- [ ] **Step 6: Run the release-gate static validation**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts web/tests/input-workbench-ui.test.ts web/tests/config-workbench-ui.test.ts web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts web/tests/results-layout.test.ts web/tests/results-workbench-state.test.ts web/tests/results-refresh.test.ts web/tests/results-view.test.ts web/tests/results-tree-chapter-status.test.ts web/tests/results-interaction.test.ts web/tests/artifacts-api.test.ts`
- `npm run lint`
- `npm run build`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/components/app-shell.tsx web/lib/app-shell-state.ts web/app/page.tsx web/app/courses/new/input/page.tsx web/app/courses/new/config/page.tsx web/app/runs/page.tsx web/app/runs/[runId]/page.tsx web/app/courses/results/page.tsx web/app/courses/[courseId]/results/page.tsx web/tests/app-shell-state.test.ts web/tests/preview-mode.test.ts web/tests/artifacts-api.test.ts
git commit -m "feat: switch product routes to stitch v2"
```

### Task 8: Update Documentation, PLANS, And Final Validation

**Files:**
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/README.md`
- Modify: `PLANS.md`

- [ ] **Step 1: Audit existing documentation and index coverage**

Create a short checklist in the task notes and verify whether these are already present or stale:

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
  - update the existing Stitch V2 migration entry if it is already present
  - only create a new entry if absent
  - include goal, scope, execution batches, and validation references

- [ ] **Step 3: Run the final validation suite**

Run:
- `node --experimental-strip-types --test web/tests/app-shell-branding.test.ts web/tests/app-shell-state.test.ts web/tests/overview-v2-workbench.test.ts web/tests/input-v2-workbench.test.ts web/tests/config-v2-workbench.test.ts web/tests/preview-mode.test.ts web/tests/results-v2-workbench.test.ts web/tests/artifacts-api.test.ts`
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
- Prefer creating presentational section components and `*-v2.tsx` workbenches over inflating the existing default workbench files further.
- Keep preview routing explicit: no product navigation should rely on `preview-run`, `preview-course`, or similar pseudo-identities.
- Tasks 2-6 are parallel-build tasks. Do not switch default `web/app/` routes to the V2 workbenches until Task 7.
- When a task creates a new V2 section component, keep it presentation-only and leave API wiring in the workbench or V2 bridge unless the plan explicitly says otherwise.
- If a task requires changing semantics instead of presentation, stop and update the spec before proceeding.
