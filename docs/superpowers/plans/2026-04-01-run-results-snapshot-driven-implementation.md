# Run / Results Snapshot-Driven Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 引入 `run_id` 级最终产物快照和新的结果读取合同，取消 Run/Results 空态路由语义，让默认产品页直接渲染未开始 Run 工作台与 snapshot 驱动的 Results 工作台。

**Architecture:** 先补 backend snapshot 存储与 read model，再让前端从旧的 `RunSession-only` / `public artifact tree` 过渡到 `UnstartedRunWorkbenchState + results-snapshot` 双数据源。snapshot 物理落在 `out/_gui/results-snapshots/<course_id>/<run_id>/chapters/<chapter_id>/notebooklm/*.md`，并通过 GUI `run_id` 显式传入 CLI/runtime；现有导出、review-summary 与兼容 artifacts API 保持存在，但默认结果树改由新的 snapshot API 驱动。

**Tech Stack:** processagent pipeline, FastAPI, Pydantic, Next.js App Router, React 19, TypeScript, Tailwind CSS, Python `unittest`, Node test runner with `--experimental-strip-types`

---

## File Map

### Backend Snapshot Contract / Read Model

- Modify: `processagent/cli.py`
- Modify: `processagent/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `server/app/models/run_session.py`
- Modify: `server/app/application/runs.py`
- Modify: `server/app/application/artifacts.py`
- Modify: `server/app/api/runs.py`
- Modify: `server/app/api/artifacts.py`
- Test: `server/tests/test_runs_api.py`
- Test: `server/tests/test_artifacts_api.py`

### Frontend Run Unstarted Workbench

- Modify: `web/app/runs/page.tsx`
- Modify: `web/app/runs/[runId]/page.tsx`
- Modify: `web/lib/app-shell-state.ts`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/components/run/run-session-workbench-v2.tsx`
- Modify: `web/components/run/run-v2-sections.tsx`
- Test: `web/tests/app-shell-state.test.ts`
- Test: `web/tests/run-v2-workbench.test.ts`
- Test: `web/tests/run-workbench-layout.test.ts`
- Test: `web/tests/preview-mode.test.ts`

### Frontend Results Snapshot Workbench

- Modify: `web/app/courses/results/page.tsx`
- Modify: `web/app/courses/[courseId]/results/page.tsx`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `web/lib/results-view.ts`
- Modify: `web/lib/results-refresh.ts`
- Modify: `web/components/results/results-workbench-v2.tsx`
- Modify: `web/components/results/results-v2-sections.tsx`
- Test: `web/tests/results-v2-workbench.test.ts`
- Test: `web/tests/results-layout.test.ts`
- Test: `web/tests/results-workbench-state.test.ts`
- Test: `web/tests/results-refresh.test.ts`
- Test: `web/tests/results-view.test.ts`
- Test: `web/tests/results-interaction.test.ts`
- Test: `web/tests/artifacts-api.test.ts`

### Documentation / Index / Cleanup

- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/README.md`
- Modify: `PLANS.md`
- Optional delete if dead after cutover: `web/components/empty/run-empty-state-v2.tsx`
- Optional delete if dead after cutover: `web/components/empty/results-empty-state-v2.tsx`

## Frozen Contract Rules

- 旧 `artifacts/*` API 保持兼容；不要在本轮直接删除。
- `review-summary` 继续维持课程级接口，不迁移到 snapshot API。
- 导出过滤继续走现有 `export` contract，不在本轮引入“按 run 导出”。
- preview 继续仅供内部调试，不变成产品默认路径。
- 输入页“课程链接”与配置页“课程级运行时覆盖”仍保持隐藏。
- Run/Results 的旧空态语义本轮会被替换，但必须同步更新 runbook 和 `PLANS.md`。

## Task 1: Add Run-Level Final-Output Snapshots And Results Snapshot APIs

**Files:**
- Modify: `processagent/cli.py`
- Modify: `processagent/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `server/app/models/run_session.py`
- Modify: `server/app/application/runs.py`
- Modify: `server/app/application/artifacts.py`
- Modify: `server/app/api/runs.py`
- Modify: `server/app/api/artifacts.py`
- Test: `server/tests/test_runs_api.py`
- Test: `server/tests/test_artifacts_api.py`

- [ ] **Step 1: Extend backend tests to describe the new contract before implementation**

补失败测试，覆盖：

- CLI / runtime 能把 GUI `run_id` 透传到 pipeline
- 章节达到 `export_ready` 时会把最终 `.md` 快照到 `out/_gui/results-snapshots/<course_id>/<run_id>/chapters/<chapter_id>/notebooklm/*.md`
- `resume same run` 覆盖当前 `run_id` 下同名 `.md`
- `clean-course` 删除当前 `run_id` snapshot，但不删历史 `run_id`
- `GET /courses/{course_id}/results-snapshot` 返回当前课程 runs、历史课程、run 状态、`snapshot_complete`
- `GET /courses/{course_id}/results-snapshot/content` 能按 `source_course_id + run_id + path` 读取 snapshot `.md`
- `run_kind = global` 不生成 snapshot，且不要求进入新的 Results 主树

- [ ] **Step 2: Run the new backend tests to verify failure**

Run:
- `python -m unittest server.tests.test_runs_api server.tests.test_artifacts_api tests.test_pipeline -v`

Expected: FAIL because snapshot storage and `results-snapshot` APIs do not exist yet.

- [ ] **Step 3: Add the snapshot lifecycle to CLI/pipeline/runtime**

在 `processagent/cli.py` 与 `processagent/pipeline.py` 中实现：

- `run-course` / `resume-course` / `clean-course` 新增可选 `--run-id`
- `PipelineConfig` / `PipelineRunner` 接收 GUI `run_id`
- 章节达到 `export_ready` 时增量复制最终 `.md`
- snapshot 路径固定为 `out/_gui/results-snapshots/<course_id>/<run_id>/chapters/<chapter_id>/notebooklm/*.md`
- 同一次 run 中允许覆盖同名文件
- `clean-course` 删除当前 `run_id` snapshot 目录

不要把 `intermediate/`、`runtime/`、`review_report.json` 复制进去。

- [ ] **Step 4: Extend backend read models and APIs**

在后端新增 snapshot-aware read model：

- `RunSession` / 相关模型补 `snapshot_complete` 或等价字段
- `ArtifactService` 新增 `results-snapshot` 列表与内容读取能力
- `runs.py` / `artifacts.py` 暴露新的结果读取接口
- `global` run 在新的 snapshot API 中明确排除

保留旧：

- `/courses/{course_id}/artifacts/tree`
- `/courses/{course_id}/artifacts/content`
- `/courses/{course_id}/review-summary`
- `/courses/{course_id}/export`

- [ ] **Step 5: Re-run backend tests**

Run:
- `python -m unittest server.tests.test_runs_api server.tests.test_artifacts_api tests.test_pipeline -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add processagent/cli.py processagent/pipeline.py tests/test_pipeline.py server/app/models/run_session.py server/app/application/runs.py server/app/application/artifacts.py server/app/api/runs.py server/app/api/artifacts.py server/tests/test_runs_api.py server/tests/test_artifacts_api.py
git commit -m "feat: add run results snapshot contract"
```

## Task 2: Replace The `/runs` Empty Route With An Unstarted Run Workbench

**Files:**
- Modify: `web/app/runs/page.tsx`
- Modify: `web/app/runs/[runId]/page.tsx`
- Modify: `web/lib/app-shell-state.ts`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/components/run/run-session-workbench-v2.tsx`
- Modify: `web/components/run/run-v2-sections.tsx`
- Test: `web/tests/app-shell-state.test.ts`
- Test: `web/tests/run-v2-workbench.test.ts`
- Test: `web/tests/run-workbench-layout.test.ts`
- Test: `web/tests/preview-mode.test.ts`

- [ ] **Step 1: Extend frontend tests to describe `/runs` as a real workbench, not an empty page**

补失败测试，覆盖：

- `/runs` 不再渲染 `RunEmptyStateV2`
- `RunSessionWorkbenchV2` 能接受未开始态数据而不是必须要 `runId`
- 未开始态会显示 `任务未开始`
- `resume` / `clean` / 日志流在未开始态下禁用
- shell 仍保留真实输入/配置/结果导航继承

- [ ] **Step 2: Run the run-page tests to verify failure**

Run:
- `cd web; node --experimental-strip-types --test tests/app-shell-state.test.ts tests/run-v2-workbench.test.ts tests/run-workbench-layout.test.ts tests/preview-mode.test.ts`

Expected: FAIL because `/runs` 目前还是空态页。

- [ ] **Step 3: Add the unstarted run read model to frontend API/types**

在 `web/lib/api/runs.ts` 与相关组件边界中补：

- `UnstartedRunWorkbenchState` 或等价类型
- 允许 `/runs` 页面在没有 `runId` 时基于 shell context 渲染工作台

不要伪造：

- `RunSession.id`
- SSE 数据
- 运行日志

- [ ] **Step 4: Replace the route and workbench wiring**

实现：

- `/runs` 直接渲染 Run V2 工作台
- `run-session-workbench-v2.tsx` 同时支持真实 run 和未开始态
- `run-v2-sections.tsx` 对未开始态展示禁用动作与明确提示

- [ ] **Step 5: Re-run run-page tests**

Run:
- `cd web; node --experimental-strip-types --test tests/app-shell-state.test.ts tests/run-v2-workbench.test.ts tests/run-workbench-layout.test.ts tests/preview-mode.test.ts`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/app/runs/page.tsx web/app/runs/[runId]/page.tsx web/lib/app-shell-state.ts web/lib/api/runs.ts web/components/run/run-session-workbench-v2.tsx web/components/run/run-v2-sections.tsx web/tests/app-shell-state.test.ts web/tests/run-v2-workbench.test.ts web/tests/run-workbench-layout.test.ts web/tests/preview-mode.test.ts
git commit -m "feat: add unstarted run workbench"
```

## Task 3: Replace The Results Empty Route And Public Artifact Tree With Snapshot-Driven Results

**Files:**
- Modify: `web/app/courses/results/page.tsx`
- Modify: `web/app/courses/[courseId]/results/page.tsx`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `web/lib/results-view.ts`
- Modify: `web/lib/results-refresh.ts`
- Modify: `web/components/results/results-workbench-v2.tsx`
- Modify: `web/components/results/results-v2-sections.tsx`
- Test: `web/tests/results-v2-workbench.test.ts`
- Test: `web/tests/results-layout.test.ts`
- Test: `web/tests/results-workbench-state.test.ts`
- Test: `web/tests/results-refresh.test.ts`
- Test: `web/tests/results-view.test.ts`
- Test: `web/tests/results-interaction.test.ts`
- Test: `web/tests/artifacts-api.test.ts`

- [ ] **Step 1: Extend results tests to describe the new snapshot tree**

补失败测试，覆盖：

- `/courses/results` 不再渲染 `ResultsEmptyStateV2`
- 默认结果树分成：
  - `过去课程产物`
  - `当前课程产物`
- 当前课程下按 `run_id -> chapter_id` 展示
- 文件树只显示最终 `.md`
- 带 `runId` 时只做 `当前 run` 标记
- `review-summary` 与导出过滤仍可用
- `global` run 不进入新的 snapshot 主树

- [ ] **Step 2: Run the results tests to verify failure**

Run:
- `cd web; node --experimental-strip-types --test tests/results-v2-workbench.test.ts tests/results-layout.test.ts tests/results-workbench-state.test.ts tests/results-refresh.test.ts tests/results-view.test.ts tests/results-interaction.test.ts tests/artifacts-api.test.ts`

Expected: FAIL because结果页目前仍依赖空态页和旧的 public artifact tree。

- [ ] **Step 3: Add snapshot-aware frontend API clients**

在 `web/lib/api/artifacts.ts` 中新增：

- `getResultsSnapshot(courseId)`
- `getResultsSnapshotContent(courseId, { sourceCourseId, runId, path })`

保留现有 `artifacts/*` 与 `buildExportUrl()` 兼容路径。

- [ ] **Step 4: Rewrite results tree helpers around snapshot sections**

在 `web/lib/results-view.ts` / `results-refresh.ts` 中重写默认树逻辑：

- 以 `results-snapshot` 为主树事实源
- 只保留目标 `.md`
- 继续保留选中与展开稳定性

- [ ] **Step 5: Replace `/courses/results` and `ResultsWorkbenchV2` wiring**

实现：

- `/courses/results` 直接渲染 Results V2 工作台
- `results-workbench-v2.tsx` 从 snapshot API 读取树与内容
- `results-v2-sections.tsx` 显示 `过去课程产物 / 当前课程产物 / 当前 run`
- 树层级为 `course_id -> run_id -> chapter_id -> md`

兼容约束：

- `review-summary` 继续走旧 API
- 导出过滤继续走旧 `export` API
- 不把中间件、runtime、review 报告塞回主树
- `global` run 完成后不要求跳进新的 Results 主树

- [ ] **Step 6: Re-run results tests**

Run:
- `cd web; node --experimental-strip-types --test tests/results-v2-workbench.test.ts tests/results-layout.test.ts tests/results-workbench-state.test.ts tests/results-refresh.test.ts tests/results-view.test.ts tests/results-interaction.test.ts tests/artifacts-api.test.ts`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/app/courses/results/page.tsx web/app/courses/[courseId]/results/page.tsx web/lib/api/artifacts.ts web/lib/results-view.ts web/lib/results-refresh.ts web/components/results/results-workbench-v2.tsx web/components/results/results-v2-sections.tsx web/tests/results-v2-workbench.test.ts web/tests/results-layout.test.ts web/tests/results-workbench-state.test.ts web/tests/results-refresh.test.ts web/tests/results-view.test.ts web/tests/results-interaction.test.ts web/tests/artifacts-api.test.ts
git commit -m "feat: add snapshot-driven results workbench"
```

## Task 4: Update Documentation, Plan Index, And Final Validation

**Files:**
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/README.md`
- Modify: `PLANS.md`
- Optional delete if dead after cutover: `web/components/empty/run-empty-state-v2.tsx`
- Optional delete if dead after cutover: `web/components/empty/results-empty-state-v2.tsx`

- [ ] **Step 1: Audit docs for now-stale empty-route semantics**

需要清掉或改写：

- `/runs` 产品空态页
- `/courses/results` 产品空态页
- 结果页仍以 public artifact tree 为主的描述

- [ ] **Step 2: Update runbooks and index**

同步更新：

- `docs/runbooks/gui-dev.md`
- `docs/runbooks/run-course.md`
- `docs/README.md`
- `PLANS.md`

要求：

- 把 snapshot 存储合同写清楚
- 把 Run 未开始态与 Results 新树结构写清楚
- 把 `_gui/results-snapshots` 的物理位置、`--run-id` 透传、以及 `global` run 的兼容行为写清楚
- 在 `PLANS.md` 中新增本轮批次，并标明它 supersede 了高保真计划中的 Run/Results 空态与结果树语义

- [ ] **Step 3: Remove dead empty-state components if they are no longer referenced**

若 `RunEmptyStateV2` / `ResultsEmptyStateV2` 已彻底无产品入口且无 preview/测试依赖，则删除；否则保留但从产品路由完全退场。

- [ ] **Step 4: Run the final validation suites**

Run:
- `python -m unittest server.tests.test_runs_api server.tests.test_artifacts_api tests.test_pipeline -v`
- `cd web; node --experimental-strip-types --test tests/app-shell-state.test.ts tests/run-v2-workbench.test.ts tests/run-workbench-layout.test.ts tests/preview-mode.test.ts tests/results-v2-workbench.test.ts tests/results-layout.test.ts tests/results-workbench-state.test.ts tests/results-refresh.test.ts tests/results-view.test.ts tests/results-interaction.test.ts tests/artifacts-api.test.ts`
- `cd web; npm run lint`
- `cd web; npm run build`

Expected: PASS

- [ ] **Step 5: Run browser smoke**

至少验证：

- `/runs`
- `/courses/results`
- `/runs/preview?mode=preview&scenario=running`
- `/courses/preview/results?mode=preview&scenario=completed`

若 backend readiness 可用，再补：

- 输入 -> 配置 -> 启动运行 -> 结果

如果被后端前置条件挡住，要明确记录阻塞，不要把 smoke 写成“已通过”。

- [ ] **Step 6: Commit**

```bash
git add docs/runbooks/gui-dev.md docs/runbooks/run-course.md docs/README.md PLANS.md web/components/empty/run-empty-state-v2.tsx web/components/empty/results-empty-state-v2.tsx
git commit -m "docs: finalize run results snapshot redesign"
```

## Notes For Execution

- 这轮不是纯前端换壳，而是一次 backend storage/read-model + frontend route semantics 的联合改造。
- `results-snapshot` 是默认结果页主树的事实源；旧 `artifacts/*` 只保留兼容与导出职责。
- snapshot 物理位置不放在 `course_dir` 内，避免与 `clean-course` 当前删除课程目录的合同冲突。
- 结果树的最深层级是 `course_id -> run_id -> chapter_id -> md`，不要把多章最终文件平铺到同一目录。
- 不要在未开始 Run 页面里伪造 `RunSession` 或 SSE 数据。
- 不要把 `review_report.json`、`intermediate/`、`runtime/*` 重新放回默认结果树。
- `global` run 继续留在兼容 artifacts/export 路径，本轮不纳入新的 snapshot 主树。
- 如需补新的 backend model，请优先复用 `server/app/models/run_session.py` 的既有建模风格。
- 如果高保真对齐计划中的 Run/Results 实现与本计划冲突，以本计划为准，并在 `PLANS.md` 明确 supersede 关系。
