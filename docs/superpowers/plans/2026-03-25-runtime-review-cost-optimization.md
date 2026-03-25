# Runtime Review / Cost Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前 GUI/CLI 运行链从“默认 review + quarantine + 自动全局汇总”调整为“默认不 review、无 quarantine、课程复用 `course_id`、全局汇总手动触发”，并补齐调用级 token 追责与两阶段 token 优化。

**Architecture:** 保持课程复用同一 `course_id`，但把章节主流程、可选 review、手动全局汇总拆成三条独立 runtime 路径。`review` 从默认门禁改为可选步骤；`quarantine` 目录与章节搬运逻辑移除；token 追责按“每次调用”落盘到 `out/` 内部运行数据；成本优化先减少调用次数，再缩减 writer payload。

**Tech Stack:** Python pipeline, FastAPI, Next.js, existing `processagent.cli`, runtime JSON artifacts under `out/`

---

## File Structure

- Modify: `processagent/pipeline.py`
- Modify: `processagent/cli.py`
- Modify: `processagent/blueprint.py`
- Modify: `processagent/llm.py`
- Modify: `server/app/application/runs.py`
- Modify: `server/app/models/course_draft.py`
- Modify: `server/app/models/run_session.py`
- Modify: `server/app/api/runs.py`
- Modify: `server/app/api/artifacts.py`
- Modify: `server/app/application/artifacts.py`
- Modify: `web/components/config/template-config-workbench.tsx`
- Modify: `web/components/run/run-session-workbench.tsx`
- Modify: `web/components/results/results-workbench.tsx`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_backends.py`
- Modify: `server/tests/test_runs_api.py`
- Modify: `server/tests/test_artifacts_api.py`
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/workstreams/blueprint-runtime.md`
- Modify: `AGENTS.md`
- Modify: `PLANS.md`

## Task 1: Remove Review As Default Runtime Gate

**Files:**
- Modify: `processagent/pipeline.py`
- Modify: `processagent/cli.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 写失败测试，覆盖默认运行不执行 review stage**
- [ ] **Step 2: 写失败测试，覆盖 review 为显式开启时才运行**
- [ ] **Step 3: 运行相关 `unittest`，确认测试先失败**
- [ ] **Step 4: 给 pipeline/CLI 增加显式 review 开关，默认值为关闭**
- [ ] **Step 5: 保持 review 作为可选步骤可单独启用，不影响章节主产物落盘**
- [ ] **Step 6: 运行相关 `unittest`，确认通过**

## Task 2: Remove Quarantine Mechanics Entirely

**Files:**
- Modify: `processagent/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `server/app/application/artifacts.py`
- Modify: `web/components/results/results-workbench.tsx`

- [ ] **Step 1: 写失败测试，覆盖 review 即使报高风险也不再搬运章节到 `quarantine/`**
- [ ] **Step 2: 运行测试，确认先失败**
- [ ] **Step 3: 删除章节搬运到 `quarantine/` 的 runtime 逻辑**
- [ ] **Step 4: 保留已有 `review_report.json` 读取能力，但结果页不再依赖 `quarantine/` 语义**
- [ ] **Step 5: 更新 artifacts 读取，确保正式章节目录始终是唯一主视图**
- [ ] **Step 6: 跑回归，确认通过**

## Task 3: Split Chapter Run From Manual Global Consolidation

**Files:**
- Modify: `processagent/pipeline.py`
- Modify: `processagent/cli.py`
- Modify: `server/app/application/runs.py`
- Modify: `server/app/api/runs.py`
- Modify: `web/components/config/template-config-workbench.tsx`
- Modify: `web/components/run/run-session-workbench.tsx`
- Modify: `tests/test_pipeline.py`
- Modify: `server/tests/test_runs_api.py`

- [ ] **Step 1: 写失败测试，覆盖章节主流程默认不重跑 `global/*`**
- [ ] **Step 2: 写失败测试，覆盖全局汇总必须通过单独触发路径执行**
- [ ] **Step 3: 运行测试，确认先失败**
- [ ] **Step 4: 拆分 pipeline 语义：章节产物主流程 vs 手动 `global` 汇总流程**
- [ ] **Step 5: 在 GUI/API 中增加“更新全局汇总”触发能力**
- [ ] **Step 6: 保持同一 `course_id` 下章节可持续追加，`global` 只在手动触发时重算**
- [ ] **Step 7: 跑回归，确认通过**

## Task 4: Add Review Control At Course Default And Per-Run Override Layers

**Files:**
- Modify: `server/app/models/course_draft.py`
- Modify: `server/app/models/run_session.py`
- Modify: `server/app/application/runs.py`
- Modify: `web/components/config/template-config-workbench.tsx`
- Modify: `web/lib/api/runs.ts`
- Modify: `server/tests/test_runs_api.py`

- [ ] **Step 1: 写失败测试，覆盖课程默认 review 设置与单次运行 override**
- [ ] **Step 2: 运行测试，确认先失败**
- [ ] **Step 3: 扩展课程配置与 run session，保存 review 默认值和 per-run override**
- [ ] **Step 4: GUI 配置页加入课程默认 review 开关；运行动作允许本次覆盖**
- [ ] **Step 5: 运行页摘要明确显示本次 run 是否启用了 review**
- [ ] **Step 6: 跑回归，确认通过**

## Task 5: Add Per-Call Token Accountability Logging

**Files:**
- Modify: `processagent/llm.py`
- Modify: `processagent/pipeline.py`
- Modify: `tests/test_backends.py`
- Modify: `docs/runbooks/run-course.md`

- [ ] **Step 1: 写失败测试，覆盖每次 LLM 调用落盘 provider/model/agent_name/tokens/duration/error**
- [ ] **Step 2: 运行测试，确认先失败**
- [ ] **Step 3: 在 backend 调用层记录单次调用级日志，落盘到 `out/` 内部运行数据**
- [ ] **Step 4: 记录字段至少包含 `course_id`、`chapter_id/global`、`stage`、`provider`、`model`、input/output tokens、耗时、结果状态**
- [ ] **Step 5: 不在 GUI 暴露此信息，只保留内部调试与追责**
- [ ] **Step 6: 跑回归，确认通过**

## Task 6: First-Phase Cost Optimization By Reducing Call Count

**Files:**
- Modify: `processagent/pipeline.py`
- Modify: `web/components/config/template-config-workbench.tsx`
- Modify: `tests/test_pipeline.py`
- Modify: `docs/runbooks/gui-dev.md`

- [ ] **Step 1: 写失败测试，覆盖模板对 writer 数量的裁剪策略**
- [ ] **Step 2: 运行测试，确认先失败**
- [ ] **Step 3: 将模板策略从“只改 prompt”扩展为“决定实际启用哪些 writer”**
- [ ] **Step 4: 让 `lecture_deep_dive`、`standard_knowledge_pack`、`interview_knowledge_base` 形成明确的 writer 组合**
- [ ] **Step 5: 保证默认关闭 review、全局汇总手动后，主流程的总调用次数显著下降**
- [ ] **Step 6: 跑回归，确认通过**

## Task 7: Second-Phase Cost Optimization By Slimming Writer Payloads

**Files:**
- Modify: `processagent/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `docs/workstreams/blueprint-runtime.md`

- [ ] **Step 1: 写失败测试，覆盖 writer 不再吃全量 transcript chunks 的新 payload 结构**
- [ ] **Step 2: 运行测试，确认先失败**
- [ ] **Step 3: 增加章节级摘要/证据摘要层，让 writer 只读取精简 payload**
- [ ] **Step 4: 保持 `curriculum_anchor` / `gap_fill` / `pack_plan` 的结构化输出不变**
- [ ] **Step 5: 确保 payload 缩减不会破坏 checkpoint/resume/invalidation 语义**
- [ ] **Step 6: 跑回归，确认通过**

## Task 8: Runtime Documentation And Validation Closure

**Files:**
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/workstreams/blueprint-runtime.md`
- Modify: `AGENTS.md`
- Modify: `PLANS.md`

- [ ] **Step 1: 更新 runbook，明确默认不 review、无 quarantine、全局汇总手动触发**
- [ ] **Step 2: 记录同课程名复用同一 `course_id` 的产品语义，以及 GUI 应优先选择已有课程**
- [ ] **Step 3: 记录 token 追责日志的落盘位置和用途，仅供内部调试**
- [ ] **Step 4: 将本轮批次写入 `PLANS.md`，只保留索引和验证入口**
- [ ] **Step 5: 运行 `python -m unittest discover -s tests -v`**
- [ ] **Step 6: 运行 `python -m unittest server.tests.test_runs_api server.tests.test_artifacts_api -v`**
- [ ] **Step 7: 运行 `npm run lint` 与 `npm run build`**
