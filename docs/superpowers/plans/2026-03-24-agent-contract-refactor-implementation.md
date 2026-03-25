# Agent Contract Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 pipeline 的 agent 输出合同，把长文本产物从大 JSON stage 拆成 planner + 多个 text writer，并把三种模板映射到统一的 writer profile。

**Architecture:** 保留 `blueprint_builder`、`curriculum_anchor`、`gap_fill`、`review` 的 JSON 合同；将 `compose_pack` 重构为 `pack_plan + 5 个 writer`，将 `canonicalize` 重构为 `2 个 writer`。pipeline 仍以 `runtime_state.json` 为 source of truth，但 step 名、checkpoint 粒度和 prompt 合同会更新，并通过新的 `pipeline_signature` 使旧输出自动失效。

**Tech Stack:** Python, existing pipeline runner, prompt markdown files, unittest

---

## File Structure

- Create: `processagent/prompts/pack_plan.md`
- Create: `processagent/prompts/write_lecture_note.md`
- Create: `processagent/prompts/write_terms.md`
- Create: `processagent/prompts/write_interview_qa.md`
- Create: `processagent/prompts/write_cross_links.md`
- Create: `processagent/prompts/write_open_questions.md`
- Create: `processagent/prompts/build_global_glossary.md`
- Create: `processagent/prompts/build_interview_index.md`
- Modify: `processagent/pipeline.py`
- Modify: `processagent/cli.py` if stage model routing names need extension
- Modify: `processagent/llm.py`
- Modify: `processagent/testing.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_cli.py`
- Modify: `server/tests/test_runs_api.py`
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/workstreams/blueprint-runtime.md`
- Modify: `PLANS.md`

## Contract Clarifications

- `target_output` 继续作为 runtime policy 的唯一持久化字段；本次不新增独立 `profile` 持久化字段
- `pack_plan.writer_profile` 只是在 planner/writer payload 中派生使用
- `LLMBackend` 这轮必须显式拆成 `generate_json()` 与 `generate_text()`
- `review` 必须读取 writer 已落盘后的完整 pack，不允许对半成品做 partial reuse
- `build_global_glossary` / `build_interview_index` 先采用保守重建策略：只要任一 chapter writer 或 active chapter 集合变化，就双双重建

## Task 1: Introduce New Prompt Surface And Stage Names

**Files:**
- Create: `processagent/prompts/pack_plan.md`
- Create: `processagent/prompts/write_lecture_note.md`
- Create: `processagent/prompts/write_terms.md`
- Create: `processagent/prompts/write_interview_qa.md`
- Create: `processagent/prompts/write_cross_links.md`
- Create: `processagent/prompts/write_open_questions.md`
- Create: `processagent/prompts/build_global_glossary.md`
- Create: `processagent/prompts/build_interview_index.md`
- Modify: `processagent/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: 写失败测试，覆盖新的 step 名出现在 runtime/checkpoint 语义中**
- [ ] **Step 1.1: 写失败测试，覆盖 `generate_text` contract 和 stub/heuristic 对齐**
- [ ] **Step 2: 运行 `python -m unittest tests.test_pipeline -v`，确认测试先失败**
- [ ] **Step 3: 在 pipeline 中引入新的 compose/canonicalize step 名常量与文件布局**
- [ ] **Step 3.1: 在 `processagent/llm.py` 和 `processagent/testing.py` 中落下 `generate_text` contract**
- [ ] **Step 4: 新建 8 个 prompt 文件，区分 JSON planner prompt 与 text writer prompt**
- [ ] **Step 5: 运行 `python -m unittest tests.test_pipeline -v`，确认新 stage 名被 pipeline 识别**

## Task 2: Split Compose Pack Into Planner + Writers

**Files:**
- Modify: `processagent/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: 写失败测试，覆盖 `compose_pack` 不再直接输出 `files` JSON**
- [ ] **Step 2: 写失败测试，覆盖 `pack_plan` 和 5 个 writer 分别产出各自文件**
- [ ] **Step 3: 运行 `python -m unittest tests.test_pipeline -v`，确认新增测试先失败**
- [ ] **Step 4: 在 pipeline 中加入 `pack_plan` JSON 调用**
- [ ] **Step 5: 在 pipeline 中加入 `write_lecture_note` / `write_terms` / `write_interview_qa` / `write_cross_links` / `write_open_questions` 文本 writer 调用**
- [ ] **Step 6: 让各 writer 直接返回 Markdown 文本，由 pipeline 写入目标文件**
- [ ] **Step 7: 保留 `review` 对产物文件的读取方式，不要求 reviewer 感知旧 `files` JSON**
- [ ] **Step 7.1: 新增测试，覆盖任一 writer 缺失/失效时 review 不得复用旧 checkpoint**
- [ ] **Step 8: 运行 `python -m unittest tests.test_pipeline -v`，确认通过**

## Task 3: Split Canonicalize Into Two Text Writers

**Files:**
- Modify: `processagent/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: 写失败测试，覆盖 `build_global_glossary` / `build_interview_index` 两个 global step**
- [ ] **Step 2: 运行 `python -m unittest tests.test_pipeline -v`，确认测试先失败**
- [ ] **Step 3: 用两个文本 writer 替代旧 `canonicalize` JSON 输出**
- [ ] **Step 4: 更新 global checkpoint 记录，分别标记两个 writer 的完成态**
- [ ] **Step 4.1: 新增测试，覆盖 active chapter 集合变化时两个 global writer 都会重建**
- [ ] **Step 5: 运行 `python -m unittest tests.test_pipeline -v`，确认通过**

## Task 4: Add Template Profile Mapping

**Files:**
- Modify: `processagent/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `docs/runbooks/run-course.md`

- [ ] **Step 1: 写失败测试，覆盖三种 `target_output` 对 writer 行为的差异映射**
- [ ] **Step 2: 运行 `python -m unittest tests.test_pipeline -v`，确认测试先失败**
- [ ] **Step 3: 在 pipeline 中引入统一 profile 解析层，但继续映射到现有 `target_output` 枚举**
- [ ] **Step 4: 让 `pack_plan` 与各 writer 都能读取 profile，而不是复制三套流程**
- [ ] **Step 5: 至少让 `write_lecture_note`、`write_terms`、`write_interview_qa`、`build_interview_index` 显式体现 profile 差异**
- [ ] **Step 6: 运行 `python -m unittest tests.test_pipeline -v`，确认通过**

## Task 5: Update Resume And Invalidation Semantics

**Files:**
- Modify: `processagent/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 写失败测试，覆盖新 writer steps 的 resume 行为**
- [ ] **Step 2: 写失败测试，覆盖 `pipeline_signature` 变化时新 writer outputs 自动失效**
- [ ] **Step 3: 运行 `python -m unittest tests.test_pipeline tests.test_cli -v`，确认测试先失败**
- [ ] **Step 4: 更新 step 有效性判定，使其覆盖 planner/writer/global writer 的新 checkpoint**
- [ ] **Step 5: 仅在必要时扩展 CLI stage-model 路由名称，不引入无用 flags**
- [ ] **Step 5.1: 更新 `server/tests/test_runs_api.py`，覆盖 GUI -> runtime 的 stage 列表和 `target_output` 兼容映射**
- [ ] **Step 6: 运行 `python -m unittest tests.test_pipeline tests.test_cli -v`，确认通过**

## Task 6: Document And Verify New Agent Contract

**Files:**
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/workstreams/blueprint-runtime.md`
- Modify: `PLANS.md`

- [ ] **Step 1: 更新 runbook，记录哪些 stage 仍是 JSON、哪些 stage 改为文本 writer**
- [ ] **Step 2: 记录三种模板如何映射到同一套 writer profile**
- [ ] **Step 3: 把这次批次写入 `PLANS.md`，仅保留索引、状态与验证入口**
- [ ] **Step 4: 运行 `python -m unittest discover -s tests -v`**
- [ ] **Step 5: 记录剩余缺口，例如 provider 级结构化输出保障、未来是否需要更细粒度 writer**
