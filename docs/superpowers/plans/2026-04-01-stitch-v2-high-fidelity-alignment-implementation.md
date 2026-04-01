# Stitch V2 High-Fidelity Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the current Stitch V2 product shell and five routed pages so their fonts, colors, spacing, iconography, shell layout, and extra-component treatment align closely with the exported Stitch code while preserving every currently wired GUI behavior.

**Architecture:** Keep the existing V2 workbench structure and backend/API contracts, but upgrade the shared design system, shell, and page presentation layers so they follow the Stitch exports much more literally. Real functionality stays in the current workbench/API boundaries; visual parity and extra-component mapping are handled through shared primitives, page sections, and context-aware action mapping.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Tailwind CSS, `next/font/google`, Node test runner with `--experimental-strip-types`, existing FastAPI-backed Web APIs

---

## File Map

### Shared Design System / Shell

- Modify: `web/app/layout.tsx`
- Modify: `web/app/globals.css`
- Modify: `web/components/app-shell.tsx`
- Modify: `web/components/stitch-v2/shell-header.tsx`
- Modify: `web/components/stitch-v2/shell-sidebar.tsx`
- Modify: `web/components/stitch-v2/page-hero.tsx`
- Modify: `web/components/stitch-v2/surface-card.tsx`
- Modify: `web/components/stitch-v2/status-chip.tsx`
- Modify: `web/components/stitch-v2/empty-state-panel.tsx`
- Create: `web/components/stitch-v2/shell-action.tsx`
- Create: `web/components/stitch-v2/material-symbol.tsx`
- Test: `web/tests/app-shell-branding.test.ts`
- Test: `web/tests/app-shell-state.test.ts`

### Overview High-Fidelity Alignment

- Modify: `web/components/overview/overview-workbench-v2.tsx`
- Create: `web/components/overview/overview-v2-sections.tsx`
- Test: `web/tests/overview-v2-workbench.test.ts`

### Input High-Fidelity Alignment

- Modify: `web/components/input/course-draft-workbench-v2.tsx`
- Modify: `web/components/input/input-v2-sections.tsx`
- Test: `web/tests/input-v2-workbench.test.ts`
- Test: `web/tests/input-workbench-ui.test.ts`

### Config High-Fidelity Alignment

- Modify: `web/components/config/template-config-workbench-v2.tsx`
- Modify: `web/components/config/config-v2-sections.tsx`
- Test: `web/tests/config-v2-workbench.test.ts`
- Test: `web/tests/config-workbench-ui.test.ts`

### Run High-Fidelity Alignment

- Modify: `web/components/run/run-session-workbench-v2.tsx`
- Modify: `web/components/run/run-v2-sections.tsx`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/run-v2-workbench.test.ts`
- Test: `web/tests/preview-mode.test.ts`
- Test: `web/tests/run-workbench-layout.test.ts`
- Test: `web/tests/run-workbench-chapter-progress.test.ts`

### Results High-Fidelity Alignment

- Modify: `web/components/results/results-workbench-v2.tsx`
- Modify: `web/components/results/results-v2-sections.tsx`
- Modify: `web/lib/results-view.ts`
- Modify: `web/lib/results-refresh.ts`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/results-v2-workbench.test.ts`
- Test: `web/tests/results-layout.test.ts`
- Test: `web/tests/results-workbench-state.test.ts`
- Test: `web/tests/results-refresh.test.ts`
- Test: `web/tests/results-view.test.ts`
- Test: `web/tests/results-tree-chapter-status.test.ts`
- Test: `web/tests/results-interaction.test.ts`
- Test: `web/tests/artifacts-api.test.ts`

### Documentation / Final Validation

- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/README.md`
- Modify: `PLANS.md`

---

## Reference Assets Root

All visual changes in this plan must reference the exported Stitch assets under:

- `out/stitch/14050487305097227160/`

Use the page-specific `.html` and `.png` files listed in the spec. Do not implement from memory when the exported code already defines spacing, font sizing, radius, and surface relationships.

## Frozen Contract Rules

- Do not change backend/API semantics.
- Do not restore course link input or course-level runtime override UI.
- Keep `AI 服务配置` collapsed by default.
- Keep `/runs` and `/courses/results` as product empty-state routes.
- Keep `mode=preview` internal-only.
- Keep results semantics: course-level latest run, scoped run label-only, filtered export, stable selection/refresh.
- Extra Stitch components must follow the mapping order from the spec:
  1. real function
  2. `即将到来`
  3. delete only if clearly irrelevant

## Task 1: Replace The Shared Visual System With Stitch Tokens, Fonts, And Icons

**Files:**
- Modify: `web/app/layout.tsx`
- Modify: `web/app/globals.css`
- Modify: `web/components/app-shell.tsx`
- Modify: `web/components/stitch-v2/shell-header.tsx`
- Modify: `web/components/stitch-v2/shell-sidebar.tsx`
- Modify: `web/components/stitch-v2/page-hero.tsx`
- Modify: `web/components/stitch-v2/surface-card.tsx`
- Modify: `web/components/stitch-v2/status-chip.tsx`
- Modify: `web/components/stitch-v2/empty-state-panel.tsx`
- Create: `web/components/stitch-v2/shell-action.tsx`
- Create: `web/components/stitch-v2/material-symbol.tsx`
- Test: `web/tests/app-shell-branding.test.ts`
- Test: `web/tests/app-shell-state.test.ts`

**Reference Assets:**
- `out/stitch/14050487305097227160/overview-v2-72223e80f4fc44f496faa80b5192e38f.html`
- `out/stitch/14050487305097227160/overview-v2-72223e80f4fc44f496faa80b5192e38f.png`

- [ ] **Step 1: Read the shell-level Stitch reference and capture the exact visual deltas**

Write down the concrete target changes:

- `Manrope + Inter` font stack
- `Material Symbols` icon system
- smaller radius scale
- lighter shell shadows
- fixed top app bar + muted side rail relationship
- top CTA / side CTA / workspace card treatment

- [ ] **Step 2: Extend the shell tests to fail on the current token/font/icon mismatch**

Add assertions for:

- `layout.tsx` imports `Manrope` and `Inter`
- shell no longer relies on `Geist` as the primary UI font
- shell/header/sidebar mention `Material Symbols`
- globals define Stitch token families close to the exported names
- shared shell action/icon wrappers exist as dedicated files

- [ ] **Step 3: Run the shell tests to confirm failure**

Run:
- `cd web; node --experimental-strip-types --test tests/app-shell-branding.test.ts tests/app-shell-state.test.ts`

Expected: FAIL until the new font, icon, and shell token system are actually wired.

- [ ] **Step 4: Replace the root typography setup**

In `layout.tsx`:

- switch to `Manrope` + `Inter`
- keep variables explicit and easy to consume from Tailwind/theme CSS
- remove the old assumption that `Geist` is the default shell font family

- [ ] **Step 5: Rewrite `globals.css` around Stitch token names and scale**

Implement:

- background/surface/outline/inverse tokens aligned with Stitch
- typography utility classes for headline/body/label roles
- radius and shadow scales closer to Stitch
- base body treatment that matches the exported shell

- [ ] **Step 6: Upgrade the shared shell primitives to literal Stitch behavior**

Required outcomes:

- `shell-header.tsx` behaves like a real top app bar
- `shell-sidebar.tsx` behaves like a side rail, not a generic nav column
- `page-hero.tsx`, `surface-card.tsx`, `status-chip.tsx`, `empty-state-panel.tsx` match the exported component proportions much more closely
- create `shell-action.tsx` and `material-symbol.tsx` so CTA buttons and icons have a shared alignment point

- [ ] **Step 7: Rework `app-shell.tsx` around the upgraded primitives**

Keep:

- four-step real navigation
- right-side context panel
- current query/context inheritance

But change the shell composition so it feels like the exported Stitch shell instead of the current engineering-first frame.

- [ ] **Step 8: Re-run the shell tests**

Run:
- `cd web; node --experimental-strip-types --test tests/app-shell-branding.test.ts tests/app-shell-state.test.ts`

Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add web/app/layout.tsx web/app/globals.css web/components/app-shell.tsx web/components/stitch-v2 web/tests/app-shell-branding.test.ts web/tests/app-shell-state.test.ts
git commit -m "feat: align shell with stitch design system"
```

## Task 2: Rebuild Overview And Shell-Level Extra Actions To Match Stitch

**Files:**
- Modify: `web/components/overview/overview-workbench-v2.tsx`
- Create: `web/components/overview/overview-v2-sections.tsx`
- Modify: `web/components/stitch-v2/shell-header.tsx`
- Modify: `web/components/stitch-v2/shell-sidebar.tsx`
- Test: `web/tests/overview-v2-workbench.test.ts`
- Test: `web/tests/app-shell-state.test.ts`

**Reference Assets:**
- `out/stitch/14050487305097227160/overview-v2-72223e80f4fc44f496faa80b5192e38f.html`
- `out/stitch/14050487305097227160/overview-v2-72223e80f4fc44f496faa80b5192e38f.png`

- [ ] **Step 1: Identify every extra Stitch shell component that appears on overview**

Classify each into:

- real function mapping
- `即将到来`
- delete

Use the spec mapping rules, not ad hoc decisions.

- [ ] **Step 2: Extend overview tests so they fail on the current low-fidelity structure**

Cover:

- overview has a dedicated `overview-v2-sections.tsx`
- hero / status / workflow cards map more directly to the Stitch structure
- top CTA and side CTA are no longer generic placeholders
- any retained non-functional shell actions are clearly marked `即将到来`

- [ ] **Step 3: Run overview tests to confirm failure**

Run:
- `cd web; node --experimental-strip-types --test tests/overview-v2-workbench.test.ts tests/app-shell-state.test.ts`

Expected: FAIL until overview structure and shell actions are rebuilt.

- [ ] **Step 4: Extract high-fidelity overview sections**

Create `overview-v2-sections.tsx` to host:

- editorial hero
- live-status block
- numbered workflow cards
- shell action CTA region

Keep the workbench responsible for real route state only.

- [ ] **Step 5: Rebuild `overview-workbench-v2.tsx` around those sections**

Required behavior:

- preserve real product navigation
- remove over-explanatory engineering copy
- align card structure, spacing, labels, and CTA grouping with Stitch

- [ ] **Step 6: Revisit shell-level CTA mapping**

In the shared shell:

- map the top CTA to a real current action where context allows, or a context-aware placeholder where it does not
- handle `New Chapter / Help / Archive` according to the spec instead of leaving them as visual noise

- [ ] **Step 7: Re-run overview/shell tests**

Run:
- `cd web; node --experimental-strip-types --test tests/overview-v2-workbench.test.ts tests/app-shell-state.test.ts`

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add web/components/overview/overview-workbench-v2.tsx web/components/overview/overview-v2-sections.tsx web/components/stitch-v2/shell-header.tsx web/components/stitch-v2/shell-sidebar.tsx web/tests/overview-v2-workbench.test.ts web/tests/app-shell-state.test.ts
git commit -m "feat: align overview and shell actions with stitch"
```

## Task 3: Align Input And Config Pages To Stitch While Preserving Current Authoring Semantics

**Files:**
- Modify: `web/components/input/course-draft-workbench-v2.tsx`
- Modify: `web/components/input/input-v2-sections.tsx`
- Modify: `web/components/config/template-config-workbench-v2.tsx`
- Modify: `web/components/config/config-v2-sections.tsx`
- Test: `web/tests/input-v2-workbench.test.ts`
- Test: `web/tests/input-workbench-ui.test.ts`
- Test: `web/tests/config-v2-workbench.test.ts`
- Test: `web/tests/config-workbench-ui.test.ts`

**Reference Assets:**
- `out/stitch/14050487305097227160/input-step1-v2-98412b91e37f42b78f70404496d85538.html`
- `out/stitch/14050487305097227160/input-step1-v2-98412b91e37f42b78f70404496d85538.png`
- `out/stitch/14050487305097227160/config-step2-v2-925e1adc724a4e948f7aff858c71d329.html`
- `out/stitch/14050487305097227160/config-step2-v2-925e1adc724a4e948f7aff858c71d329.png`

- [ ] **Step 1: Compare current Input/Config V2 against the Stitch layouts**

List exact gaps for:

- hero proportions
- upload/control panel framing
- muted side surfaces
- CTA treatment
- form spacing
- section label styling

- [ ] **Step 2: Extend Input/Config tests to fail on low-fidelity leftovers**

Cover:

- Input uses Stitch-like upload + supporting card structure
- Config uses Stitch-like control core + summary/supporting rail
- course link UI remains absent
- AI 服务配置 remains collapsed by default
- course-level runtime override remains hidden
- any extra visual cards that do not map to real features are explicitly `即将到来`

- [ ] **Step 3: Run Input/Config tests to confirm failure**

Run:
- `cd web; node --experimental-strip-types --test tests/input-v2-workbench.test.ts tests/input-workbench-ui.test.ts tests/config-v2-workbench.test.ts tests/config-workbench-ui.test.ts`

Expected: FAIL until the page sections are rebuilt at the new fidelity target.

- [ ] **Step 4: Rebuild `input-v2-sections.tsx` and `course-draft-workbench-v2.tsx`**

Required behavior:

- keep local file upload
- keep manual subtitle asset editing
- keep draft summary and route to config
- map extra Stitch cards to current/future authoring semantics
- do not reintroduce course-link UI

- [ ] **Step 5: Rebuild `config-v2-sections.tsx` and `template-config-workbench-v2.tsx`**

Required behavior:

- make template controls visually dominant
- keep AI 服务配置 collapsed but visually aligned to Stitch
- keep start/continue run and global build actions
- do not surface hidden runtime override UI

- [ ] **Step 6: Re-run Input/Config tests**

Run:
- `cd web; node --experimental-strip-types --test tests/input-v2-workbench.test.ts tests/input-workbench-ui.test.ts tests/config-v2-workbench.test.ts tests/config-workbench-ui.test.ts`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/components/input/course-draft-workbench-v2.tsx web/components/input/input-v2-sections.tsx web/components/config/template-config-workbench-v2.tsx web/components/config/config-v2-sections.tsx web/tests/input-v2-workbench.test.ts web/tests/input-workbench-ui.test.ts web/tests/config-v2-workbench.test.ts web/tests/config-workbench-ui.test.ts
git commit -m "feat: align input and config with stitch"
```

## Task 4: Align Run And Results Pages To Stitch While Preserving Runtime Semantics

**Files:**
- Modify: `web/components/run/run-session-workbench-v2.tsx`
- Modify: `web/components/run/run-v2-sections.tsx`
- Modify: `web/components/results/results-workbench-v2.tsx`
- Modify: `web/components/results/results-v2-sections.tsx`
- Modify: `web/lib/results-view.ts`
- Modify: `web/lib/results-refresh.ts`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `web/lib/preview/workbench.ts`
- Test: `web/tests/run-v2-workbench.test.ts`
- Test: `web/tests/run-workbench-layout.test.ts`
- Test: `web/tests/run-workbench-chapter-progress.test.ts`
- Test: `web/tests/results-v2-workbench.test.ts`
- Test: `web/tests/results-layout.test.ts`
- Test: `web/tests/results-workbench-state.test.ts`
- Test: `web/tests/results-refresh.test.ts`
- Test: `web/tests/results-view.test.ts`
- Test: `web/tests/results-tree-chapter-status.test.ts`
- Test: `web/tests/results-interaction.test.ts`
- Test: `web/tests/artifacts-api.test.ts`
- Test: `web/tests/preview-mode.test.ts`

**Reference Assets:**
- `out/stitch/14050487305097227160/run-step3-v2-2732c03d32c84715a16587ceed205b9b.html`
- `out/stitch/14050487305097227160/run-step3-v2-2732c03d32c84715a16587ceed205b9b.png`
- `out/stitch/14050487305097227160/results-step4-v2-4d882ed4de034a6aa99c5bfe1123da05.html`
- `out/stitch/14050487305097227160/results-step4-v2-4d882ed4de034a6aa99c5bfe1123da05.png`

- [ ] **Step 1: Compare current Run/Results V2 against Stitch**

Record the exact visual mismatches in:

- metric/header framing
- chapter board density
- dark/light panel balance
- file tree / preview / export proportions
- badge, CTA, and warning styles

- [ ] **Step 2: Extend Run/Results tests to fail on low-fidelity structure and shell-action treatment**

Cover:

- run/results sections are now shaped around Stitch-like panel proportions
- preview mode still stays internal-only
- results semantics stay course-level latest-run + scoped-run-label-only
- export controls remain real
- any retained extra actions are either real or marked `即将到来`

- [ ] **Step 3: Run Run/Results tests to confirm failure**

Run:
- `cd web; node --experimental-strip-types --test tests/run-v2-workbench.test.ts tests/run-workbench-layout.test.ts tests/run-workbench-chapter-progress.test.ts tests/results-v2-workbench.test.ts tests/results-layout.test.ts tests/results-workbench-state.test.ts tests/results-refresh.test.ts tests/results-view.test.ts tests/results-tree-chapter-status.test.ts tests/results-interaction.test.ts tests/artifacts-api.test.ts tests/preview-mode.test.ts`

Expected: FAIL until the higher-fidelity section rebuild is in place.

- [ ] **Step 4: Rebuild `run-v2-sections.tsx` and `run-session-workbench-v2.tsx`**

Required behavior:

- keep run summary, chapter progress, logs, resume/clean
- align panels and CTA hierarchy to Stitch
- keep preview route contract unchanged

- [ ] **Step 5: Rebuild `results-v2-sections.tsx` and `results-workbench-v2.tsx`**

Required behavior:

- keep course-level latest run semantics
- keep scoped run label-only semantics
- keep export filter semantics
- keep stable tree refresh and selection
- align panel ratios and surface hierarchy to Stitch

- [ ] **Step 6: Adjust shared results helpers only as needed**

Keep helper changes minimal and presentation-driven:

- `results-view.ts`
- `results-refresh.ts`
- `artifacts.ts`
- `preview/workbench.ts`

Do not change backend contract assumptions.

- [ ] **Step 7: Re-run Run/Results tests**

Run:
- `cd web; node --experimental-strip-types --test tests/run-v2-workbench.test.ts tests/run-workbench-layout.test.ts tests/run-workbench-chapter-progress.test.ts tests/results-v2-workbench.test.ts tests/results-layout.test.ts tests/results-workbench-state.test.ts tests/results-refresh.test.ts tests/results-view.test.ts tests/results-tree-chapter-status.test.ts tests/results-interaction.test.ts tests/artifacts-api.test.ts tests/preview-mode.test.ts`

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add web/components/run/run-session-workbench-v2.tsx web/components/run/run-v2-sections.tsx web/components/results/results-workbench-v2.tsx web/components/results/results-v2-sections.tsx web/lib/results-view.ts web/lib/results-refresh.ts web/lib/api/artifacts.ts web/lib/preview/workbench.ts web/tests/run-v2-workbench.test.ts web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts web/tests/results-v2-workbench.test.ts web/tests/results-layout.test.ts web/tests/results-workbench-state.test.ts web/tests/results-refresh.test.ts web/tests/results-view.test.ts web/tests/results-tree-chapter-status.test.ts web/tests/results-interaction.test.ts web/tests/artifacts-api.test.ts web/tests/preview-mode.test.ts
git commit -m "feat: align run and results with stitch"
```

## Task 5: Audit Route-Level Fidelity, Browser Screens, And Documentation

**Files:**
- Modify: `web/app/page.tsx`
- Modify: `web/app/courses/new/input/page.tsx`
- Modify: `web/app/courses/new/config/page.tsx`
- Modify: `web/app/runs/page.tsx`
- Modify: `web/app/runs/[runId]/page.tsx`
- Modify: `web/app/courses/results/page.tsx`
- Modify: `web/app/courses/[courseId]/results/page.tsx`
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/README.md`
- Modify: `PLANS.md`

- [ ] **Step 1: Audit every routed page for leftover non-Stitch scaffolding**

Look for:

- old page wrappers
- duplicated page headers
- old explanatory copy
- route-specific style exceptions that break the shared shell

- [ ] **Step 2: Add any final route-level assertions needed**

Cover:

- default routes still use the V2 workbenches
- preview routes remain explicit
- product empty routes remain product empty routes
- route-level query inheritance still works after shell/action changes

- [ ] **Step 3: Run the route-level tests to confirm current gaps**

Run:
- `cd web; node --experimental-strip-types --test tests/app-shell-state.test.ts tests/preview-mode.test.ts`

Expected: FAIL only if the route-level shell cleanup actually changes route wiring assumptions; otherwise proceed directly to implementation and rerun as a safety check.

- [ ] **Step 4: Apply final route/documentation cleanup**

Update:

- page files so they no longer carry stale non-Stitch copy
- `gui-dev.md` to document the higher-fidelity Stitch baseline
- `docs/README.md` to refresh the GUI baseline
- `PLANS.md` to add this alignment batch entry and validation set

- [ ] **Step 5: Run the final static validation suite**

Run:
- `cd web; node --experimental-strip-types --test tests/app-shell-branding.test.ts tests/app-shell-state.test.ts tests/overview-v2-workbench.test.ts tests/input-v2-workbench.test.ts tests/input-workbench-ui.test.ts tests/config-v2-workbench.test.ts tests/config-workbench-ui.test.ts tests/run-v2-workbench.test.ts tests/run-workbench-layout.test.ts tests/run-workbench-chapter-progress.test.ts tests/results-v2-workbench.test.ts tests/results-layout.test.ts tests/results-workbench-state.test.ts tests/results-refresh.test.ts tests/results-view.test.ts tests/results-tree-chapter-status.test.ts tests/results-interaction.test.ts tests/artifacts-api.test.ts tests/preview-mode.test.ts`
- `cd web; npm run lint`
- `cd web; npm run build`

Expected: PASS

- [ ] **Step 6: Run browser-level fidelity smoke**

Verify at minimum:

- `/`
- `/courses/new/input`
- `/courses/new/config`
- `/runs`
- `/courses/results`
- `/runs/preview?mode=preview&scenario=running`
- `/courses/preview/results?mode=preview&scenario=completed`

If backend is ready, also verify:

- `Input -> Config -> Run -> Results`

Record any backend-readiness blocker explicitly instead of hand-waving it.

- [ ] **Step 7: Commit**

```bash
git add web/app/page.tsx web/app/courses/new/input/page.tsx web/app/courses/new/config/page.tsx web/app/runs/page.tsx web/app/runs/[runId]/page.tsx web/app/courses/results/page.tsx web/app/courses/[courseId]/results/page.tsx docs/runbooks/gui-dev.md docs/README.md PLANS.md
git commit -m "docs: finalize stitch high-fidelity alignment"
```

## Notes For Execution

- This is a visual/shell alignment plan, not a feature-addition plan.
- Preserve every currently wired GUI contract unless the spec explicitly reclassifies the component as visual-only or `即将到来`.
- Prefer shared presentation primitives over one-off page-local CSS exceptions.
- Treat Stitch HTML as a layout and styling reference, not as a source of fake product semantics.
- If a Stitch extra action cannot honestly map to a real function, mark it `即将到来` instead of inventing a fake action.
- Keep pages readable on desktop and mobile while moving closer to Stitch proportions.
