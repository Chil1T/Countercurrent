# GUI Config And Runflow Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Execution status:** Completed on 2026-03-25. `PLANS.md` is the source of truth for batch status; the checklist below is retained as the original implementation breakdown.

**Goal:** Refine GUI configuration, context summaries, results-tree behavior, and run-resume semantics so users see the real runtime state and can safely retry hosted runs with updated provider routing.

**Architecture:** Keep the existing blueprint-first runtime and four-page GUI shell. Make targeted changes at the GUI display boundary, the server-side run orchestration boundary, and the pipeline execution boundary so frozen pipeline identity and refreshable provider routing are handled separately.

**Tech Stack:** Next.js, TypeScript, FastAPI, Pydantic, Python unittest, existing processagent CLI/runtime.

---

## File Map

### Frontend

- Modify: `web/lib/context-panel.ts`
- Modify: `web/components/context-panel.tsx`
- Modify: `web/components/config/template-config-workbench.tsx`
- Modify: `web/components/results/results-workbench.tsx`
- Modify: `web/lib/results-view.ts`
- Modify: `web/app/courses/[courseId]/results/page.tsx`
- Modify: `web/lib/api/runs.ts`
- Test: `web/tests/context-panel.test.ts`
- Test: `web/tests/results-view.test.ts`
- Test: `web/tests/results-layout.test.ts`

### Server / Runtime

- Modify: `server/app/application/runs.py`
- Modify: `server/app/adapters/cli_runner.py`
- Modify: `server/app/models/run_session.py`
- Modify: `server/app/models/template_preset.py` if new config typing is needed
- Test: `server/tests/test_runs_api.py`
- Test: `server/tests/test_artifacts_api.py`

### Pipeline

- Modify: `processagent/pipeline.py`
- Modify: `processagent/cli.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_cli.py`

### Documentation

- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/workstreams/blueprint-runtime.md`
- Modify: `AGENTS.md`
- Modify: `processagent/AGENTS.md`
- Modify: `PLANS.md`

---

### Task 1: 修正 Context 栏显示语义

**Files:**
- Modify: `web/lib/context-panel.ts`
- Modify: `web/components/context-panel.tsx`
- Test: `web/tests/context-panel.test.ts`

- [ ] **Step 1: 写出 Context 栏失败测试**

覆盖以下场景：
- `asset_completeness=60` 时显示 `60%` 而不是 `6000%`
- 有 `run` 时，后端和模型显示优先读取 `RunSession`
- 无 `run` 时，`运行摘要` 使用用户提示文案

- [ ] **Step 2: 运行前端测试确认失败**

Run: `node --test --experimental-strip-types web\\tests\\context-panel.test.ts`
Expected: 至少一条断言失败，证明旧逻辑仍在乘以 100 或优先读取 draft 配置。

- [ ] **Step 3: 最小化实现 Context 栏修正**

在 `web/lib/context-panel.ts` 中：
- 去掉 `asset_completeness * 100`
- 将 `运行摘要` 占位文案改成用户语言
- 当 `run` 存在时，模板/运行摘要优先使用 `run.backend`、`run.simple_model`、`run.complex_model`

必要时在 `web/components/context-panel.tsx` 中补齐数据装配。

- [ ] **Step 4: 重新运行测试**

Run: `node --test --experimental-strip-types web\\tests\\context-panel.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/lib/context-panel.ts web/components/context-panel.tsx web/tests/context-panel.test.ts
git commit -m "fix: correct context panel runtime summaries"
```

### Task 2: 收敛配置页主路径并优化文案

**Files:**
- Modify: `web/components/config/template-config-workbench.tsx`

- [ ] **Step 1: 写出配置页结构断言或组件测试**

覆盖以下行为：
- `启用 Review` 文案与帮助文案正确
- `课程级运行覆盖` 默认折叠到高级设置
- `内容密度` 与 `Review 策略` 使用统一横向布局

- [ ] **Step 2: 运行相关测试或 lint，确认旧结构未满足**

Run: 为 Step 1 写出的组件/结构测试
Expected: FAIL，证明旧文案、默认展示路径或字段布局仍未满足需求。

- [ ] **Step 3: 最小化实现配置页收敛**

在 `web/components/config/template-config-workbench.tsx` 中：
- 将 review 选项改名为 `启用 Review`
- 用用户语言重写帮助文案
- 把 `课程级运行覆盖` 放入 `高级设置`
- 调整 `内容密度` / `Review 策略` 成为一致的横向字段布局

- [ ] **Step 4: 运行前端 lint**

Run:
- Step 1 写出的组件/结构测试
- `npm run lint`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/components/config/template-config-workbench.tsx
git commit -m "feat: simplify config page primary workflow"
```

### Task 3: 重构结果页文件树为层级结构并补加载态

**Files:**
- Modify: `web/components/results/results-workbench.tsx`
- Modify: `web/lib/results-view.ts`
- Modify: `web/app/courses/[courseId]/results/page.tsx`
- Modify: `web/lib/api/runs.ts`
- Test: `web/tests/results-view.test.ts`
- Test: `web/tests/results-layout.test.ts`

- [ ] **Step 1: 写出结果页树结构失败测试**

覆盖以下行为：
- 文件树按章节 / 最终产物 / 中间数据分层
- 结果页基于真实 `RunSession` 状态决定是否显示加载提示
- 文件节点为中性卡片，层级选中态为深色

- [ ] **Step 2: 运行测试确认旧实现仍是扁平列表**

Run: `node --test --experimental-strip-types web\\tests\\results-view.test.ts`
Expected: FAIL，证明旧实现仍是扁平视图，且结果页还不知道 `run` 状态。

- [ ] **Step 3: 实现层级树与加载态**

在 `web/lib/results-view.ts` 中增加：
- 路径分层 helper
- 节点展开/选中辅助逻辑

在 `web/app/courses/[courseId]/results/page.tsx` / `web/lib/api/runs.ts` / `web/components/results/results-workbench.tsx` 中：
- 将 `runId` 与 `RunSession` 状态传入结果页
- 以章节树替代扁平文件卡片
- 在真实 run 未完成时显示“文件仍在生成中”提示
- 保持预览区路径信息在右侧头部

- [ ] **Step 4: 运行结果页测试与 lint**

Run:
- `node --test --experimental-strip-types web\\tests\\results-view.test.ts`
- `node --test --experimental-strip-types web\\tests\\results-layout.test.ts`
- `npm run lint`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/app/courses/[courseId]/results/page.tsx web/lib/api/runs.ts web/components/results/results-workbench.tsx web/lib/results-view.ts web/tests/results-view.test.ts web/tests/results-layout.test.ts
git commit -m "feat: add hierarchical results tree"
```

### Task 4: 将 resume 语义拆成“流水线锁定 + 供应商配置刷新”

**Files:**
- Modify: `server/app/application/runs.py`
- Modify: `server/app/models/run_session.py`
- Modify: `server/app/adapters/cli_runner.py`
- Modify: `processagent/cli.py`
- Test: `server/tests/test_runs_api.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: 写出后端失败测试**

覆盖以下行为：
- 第一次 run 冻结 `target_output`、`content_density` 语义、`review_enabled`、`review_mode`、run kind 和 stage graph
- `resume` 前切换 GUI 默认 provider/base URL/model 后，会读取新 provider routing
- 清空课程级 override 后，会回退到 GUI 默认值而不是旧 run 快照
- `resume` 后 `RunSession` 的 hosted 配置字段更新为新值

- [ ] **Step 2: 运行后端测试确认旧实现仍沿用旧 provider**

Run:
- `python -m unittest server.tests.test_runs_api -v`
- `python -m unittest tests.test_cli -v`

Expected: FAIL，证明 `resume` 仍完全复用旧 `RunSession` hosted 配置，且 CLI/runtime 仍允许通过 resume 路径改动流水线身份。

- [ ] **Step 3: 实现运行身份与 provider routing 分离**

在 `server/app/application/runs.py` 中：
- 为 resume 增加“刷新 hosted routing”逻辑
- 保持 `target_output`、`review_enabled`、`review_mode`、writer 集和 stage 图不变
- 让 `_start_process()` 使用刷新后的 provider/base URL/model/timeout

在 `processagent/cli.py` 中：
- 收紧 `resume-course` 路径上的 policy override 面
- 明确只允许 provider routing 类参数在恢复时变化

必要时在 `server/app/models/run_session.py` 中补明确字段。

- [ ] **Step 4: 运行后端测试**

Run: `python -m unittest server.tests.test_runs_api -v`
Run:
- `python -m unittest server.tests.test_runs_api -v`
- `python -m unittest tests.test_cli -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/app/application/runs.py server/app/models/run_session.py server/app/adapters/cli_runner.py processagent/cli.py server/tests/test_runs_api.py tests/test_cli.py
git commit -m "feat: refresh provider routing on resume"
```

### Task 5: 审计高 provider 压力阶段并确定并发治理边界

**Files:**
- Modify: `processagent/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: 写出 provider 压力审计测试或断言**

覆盖以下行为：
- runtime 明确标识哪些阶段会产生 provider 压力
- 当前 chapter loop / writer loop / global build 是串行还是 fan-out 有清晰结论
- 为未来并发控制预留明确落点，但不强行引入无用 CLI flag

- [ ] **Step 2: 运行 Python 测试确认当前缺少显式说明**

Run: `python -m unittest tests.test_pipeline -v`

Expected: FAIL，证明当前 runtime 对 provider 压力阶段与串/并行边界没有显式 contract。

- [ ] **Step 3: 最小化实现并发治理边界**

在 `processagent/pipeline.py` 中：
- 标注高 provider 压力阶段
- 明确当前执行是串行还是 fan-out
- 记录未来并发上限的正确挂点，但不引入无效配置

- [ ] **Step 4: 运行 Python 测试**

Run: `python -m unittest tests.test_pipeline -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add processagent/pipeline.py tests/test_pipeline.py
git commit -m "docs: clarify hosted pressure points"
```

### Task 6: 文档、规则与批次索引收口

**Files:**
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/workstreams/blueprint-runtime.md`
- Modify: `AGENTS.md`
- Modify: `processagent/AGENTS.md`
- Modify: `PLANS.md`

- [ ] **Step 1: 更新 runbook**

在 `docs/runbooks/gui-dev.md` 与 `docs/runbooks/run-course.md` 中补齐：
- `启用 Review` 的默认关闭语义
- `resume` 的新语义：流水线锁定、provider routing 刷新
- 结果页层级树与加载态说明
- 并发高风险阶段与默认限制说明

- [ ] **Step 2: 更新 workstream 与 AGENTS 入口**

在 `docs/workstreams/blueprint-runtime.md`、`AGENTS.md`、`processagent/AGENTS.md` 中补：
- 运行身份与 provider routing 的边界
- 并发治理与高风险阶段说明
- Context/GUI 展示应优先反映生效 runtime 值

- [ ] **Step 3: 更新 `PLANS.md`**

登记本批次状态、范围与验证命令，并将文档收口列为最后执行批次。

- [ ] **Step 4: 运行最终验证**

Run:
- `python -m unittest discover -s tests -v`
- `python -m unittest server.tests.test_runs_api server.tests.test_artifacts_api -v`
- `npm run lint`
- `npm run build`

Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add docs/runbooks/gui-dev.md docs/runbooks/run-course.md docs/workstreams/blueprint-runtime.md AGENTS.md processagent/AGENTS.md PLANS.md
git commit -m "docs: align gui runflow refinement guidance"
```

---

## Plan Review Notes

- Keep implementation incremental. Do not mix Task 4 runtime semantics with Task 3 results-tree UI unless a shared contract change makes it unavoidable.
- Preserve existing runtime artifact locations under `out/`.
- Avoid adding new dependencies; use existing React/FastAPI/Python patterns.
