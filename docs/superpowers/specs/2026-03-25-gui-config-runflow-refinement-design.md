# GUI Config And Runflow Refinement Design

**Date:** 2026-03-25

**Status:** approved-for-planning

**Goal**

Refine the GUI configuration page, context summary, results tree, and run-resume semantics so the product reflects the real runtime state, reduces user confusion, and preserves stable pipeline identity while allowing hosted provider configuration to change between retries.

## Context

The current GUI already supports real hosted backends, per-call LLM accountability logging, and a four-step workflow (`输入 -> 配置 -> 运行 -> 结果`). Recent manual testing exposed three classes of issues:

1. The configuration page still carries internal-facing language and low-value controls that make the page feel heavier than necessary.
2. The right-side `Context` panel and results page surface stale or misleading information because they derive from draft state instead of the active run snapshot.
3. The run/resume contract is currently too rigid for hosted provider recovery. Users want to retry after switching provider credentials and routing without changing the course pipeline mode.

This design addresses those issues without changing the core blueprint-first runtime model.

## Accepted Product Decisions

### 1. Resume semantics

`resume` will be split into two configuration classes:

- **Locked run identity**
  - `target_output`
  - `content_density`
  - `review_enabled`
  - `review_mode`
  - active writer set / stage graph
  - chapter/global run kind
- **Refreshable provider routing**
  - `provider`
  - `base_url`
  - `api_key`
  - `simple_model`
  - `complex_model`
  - `timeout_seconds`

This keeps checkpoint meaning stable while still allowing users to recover from quota exhaustion, rate limits, or provider migration.

### 2. Course identity and cross-chapter workflow

The project will continue to reuse one `course_id` per course title. GUI flows should bias toward selecting an existing course rather than creating near-duplicate titles. Cross-chapter outputs (`global/*`) remain a manual action and are not part of the main single-chapter run path.

### 3. Review behavior

`review` remains optional, default-off, with both course default and per-run override. The GUI should explain it as a quality-improvement option instead of an internal control surface.

### 4. Token accountability

Per-call LLM accountability remains an internal runtime facility only. It should stay in `out/courses/<course_id>/runtime/llm_calls.jsonl` and not surface in the end-user GUI.

## Scope

### In scope

- Configuration-page copy and layout refinements
- Context panel correctness fixes
- Results tree restructuring and loading feedback
- Resume contract update for hosted provider routing refresh
- Concurrency-stage audit and runtime concurrency controls
- Related runbook / AGENTS / plan index updates

### Out of scope

- New user-facing billing/token dashboard
- New course picker UI for the input page in this batch
- Replacing the current shell layout again
- Reworking blueprint-first runtime artifacts beyond what is required for the new resume contract and results tree

## Design

### A. Configuration Page

#### A1. User-facing review copy

The course default review control will be renamed to `启用 Review`.

Help copy will be user-facing:

> 开启后，系统会在生成过程中增加 Review 环节，以帮助提升结果质量。默认关闭。

This copy should appear wherever the course-level default is edited. The per-run override should also be phrased in the same style.

#### A2. Configuration complexity reduction

The current `课程级运行覆盖` block is useful but too heavy for the common path. It will be moved under an `高级设置` container instead of being shown as a first-class section in the default viewport.

The default-provider card remains the primary hosted configuration surface.

#### A3. Parameter editor layout

`内容密度` and `Review 策略` will be laid out horizontally using the same field geometry as neighboring parameter controls. The goal is visual consistency and better scanability.

#### A4. Provider card visibility

The current default-provider area will continue to show only the card for the active default provider. Switching provider will swap the visible card. `heuristic` remains a copy-only state with no hosted credential form.

### B. Context Panel

#### B1. Placeholder copy

When no run exists yet, `运行摘要` should display user-facing guidance rather than internal implementation notes.

Accepted wording direction:

- `运行开始后，这里将显示本次任务的关键信息与执行摘要。`

#### B2. Course summary correctness

`素材完整度` currently multiplies an already normalized 0-100 field and can produce values like `6000%`. The panel must display the value directly as a bounded percentage.

#### B3. Effective runtime display

When a run exists, the context panel should prefer the active `RunSession` snapshot for:

- backend/provider
- hosted/base URL
- simple model
- complex model
- runtime status summary

When no run exists, it may fall back to draft-level configuration. This avoids showing `heuristic` or `未配置` while the actual run is using a hosted provider.

### C. Results Page

#### C1. Loading state

When the run has not completed, the results tree should explicitly show that files are still being generated. The user should never have to infer “empty means still running”.

#### C2. Tree structure

The current flat file list will be replaced with a hierarchical tree:

- chapter
  - final artifacts
  - intermediate artifacts
  - files
- global
  - files
- runtime
  - files

Expanded levels should use a darker selected state. File cards themselves should become neutral instead of brightly color-coded. Path detail remains in the preview header, not in the tree rows.

### D. Run/Resume Contract

#### D1. Frozen pipeline identity

The first run snapshot remains the authority for:

- run kind (`chapter` vs `global`)
- target output profile
- content density profile
- review enablement for that run
- review mode for that run
- active writer set
- stage list shown in GUI

Resume must not mutate these values.

#### D2. Refreshed provider routing

Resume will resolve the latest effective provider routing before launching the subprocess:

- latest course-level override values
- then latest GUI default provider settings
- then CLI/runtime defaults for any still-missing values
- latest API key/base URL/model/timeout after the above precedence is applied

The resumed run should overwrite its stored hosted configuration fields with those refreshed values before subprocess launch so that GUI summaries and errors stay aligned with the actual retry.

If a course-level override field is cleared, resume should fall back to GUI defaults rather than preserve the stale value from the failed run snapshot.

#### D3. Results-page run awareness

The results page loading state must be driven by real run state, not by guessing from the current artifact tree. The page should receive `runId`, load the corresponding `RunSession`, and use that runtime status to decide whether to show:

- loading / still generating
- completed results
- failed run with partial artifacts

“Empty tree means still running” is explicitly not allowed.

### E. Concurrency Governance

#### E1. Audit

The implementation will identify which runtime stages can produce provider pressure. Based on the current pipeline shape, likely high-risk stages are:

- chapter writer stages when multiple chapters are processed in one run
- optional review when enabled
- manual global build over many completed chapters

#### E2. Concurrency limits

The current implementation is predominantly serialized. This batch will first document and make explicit where provider pressure can happen, then decide whether runtime concurrency controls are actually needed. A new CLI/runtime concurrency flag is not mandatory unless the audit reveals a real fan-out path in current code.

Minimum batch requirement:

- document current provider-pressure stages
- state whether the current code is serialized or fan-out based
- record the recommended place for a future concurrency ceiling if parallel chapter/global execution is introduced

This does not require a GUI control in this batch; backend/runtime defaults and documentation are sufficient.

## Data And File Responsibilities

### Existing files expected to change

- `web/lib/context-panel.ts`
- `web/components/context-panel.tsx`
- `web/components/config/template-config-workbench.tsx`
- `web/components/results/results-workbench.tsx`
- `web/lib/results-view.ts`
- `web/app/courses/[courseId]/results/page.tsx`
- `web/lib/api/runs.ts`
- `server/app/application/runs.py`
- `server/app/adapters/cli_runner.py`
- `server/app/models/run_session.py`
- `processagent/pipeline.py`
- `processagent/cli.py`
- `docs/runbooks/gui-dev.md`
- `docs/runbooks/run-course.md`
- `docs/workstreams/blueprint-runtime.md`
- `AGENTS.md`
- `processagent/AGENTS.md`
- `PLANS.md`

### Likely test files

- `server/tests/test_runs_api.py`
- `server/tests/test_artifacts_api.py`
- `tests/test_pipeline.py`
- `tests/test_cli.py`
- `web/tests/results-view.test.ts`
- `web/tests/results-layout.test.ts`
- `web/tests/context-panel.test.ts`

## Validation Strategy

- Python runtime and server regressions:
  - `python -m unittest discover -s tests -v`
  - `python -m unittest server.tests.test_runs_api server.tests.test_artifacts_api -v`
- Frontend checks:
  - `npm run lint`
  - `npm run build`
- Targeted browser/manual verification:
  - hosted run with provider switch and resume
  - incomplete run showing results-tree loading state
  - context panel showing effective hosted provider/model values

## Risks

- Changing resume semantics can silently invalidate user expectations unless the UI copy is explicit.
- Results tree hierarchy changes can regress selection and preview behavior if flat-path assumptions remain in helper utilities.
- Concurrency controls must not accidentally break existing checkpoint/resume behavior.

## Done Criteria

- Config page copy and layout match accepted user-facing semantics.
- Context panel shows bounded completeness and effective runtime backend/model values.
- Results page exposes loading state and hierarchical tree navigation.
- Resume refreshes provider routing but keeps pipeline identity fixed.
- Concurrency-pressure stages are documented and guarded by explicit runtime limits.
- Runbooks, workstreams, and AGENTS pointers are updated to match the new behavior.
