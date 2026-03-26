# GUI Web Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `databaseleaning` 建立一个本地优先、前后端分离、可继续部署的 Web GUI v1，覆盖输入、配置、运行、结果四页主流程，并以真实 CLI/runtime contract 作为运行 source of truth。

**Architecture:** 在仓库根新增 `web/` 与 `server/` 两个子系统。`web/` 使用 Next.js 构建产品壳层与四页流程；`server/` 使用 FastAPI 建立稳定 API、运行编排与 CLI adapter。GUI 只能通过运行前置条件校验后触发 `processagent.cli`，阶段状态由 `course_blueprint.json` 与 `runtime_state.json` 映射，实时更新通过 `SSE` 推送。

**Tech Stack:** Next.js, TypeScript, Tailwind CSS, FastAPI, Pydantic, Python subprocess, SSE

---

## Delivery Status

### Completed Batches

1. 前端壳层与四页基础路由
2. FastAPI 服务骨架与产品 DTO
3. 输入页最小可执行输入：教材名 + 字幕文本
4. 配置页模板配置与运行启动
5. 真实 `LocalProcessRunner`、`runtime_state` 映射、结果页 tree/preview/export
6. `resume` / `clean` 控制动作与 `SSE` 运行事件流

### Remaining Batches

无。GUI v1 当前批次已收口。

## Completed Work Notes

已完成部分不再逐项执行，但保留关键边界，供后续批次继承：

- `CourseDraft` 只有在存在真实 transcript input 时才允许启动/恢复运行
- CLI adapter 逐个按 subcommand 契约拼装参数，不能共享同一组 flags
- `cleaned` 状态会清空阶段轨道，不复用旧的 completed UI
- `SSE` 断线只显示告警，不直接把运行页切成失败态

---

### Task 7: Add Runtime Log Panel And Log Read APIs

**Files:**
- Modify: `server/app/adapters/cli_runner.py`
- Modify: `server/app/application/runs.py`
- Modify: `server/app/api/runs.py`
- Modify: `server/app/models/run_session.py`
- Modify: `server/tests/test_runs_api.py`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/components/run/run-session-workbench.tsx`

- [x] **Step 1: 写失败测试，覆盖 run 日志读取与缺失日志时的返回约定**
- [x] **Step 2: 运行 `python -m unittest server.tests.test_runs_api -v`，确认新增测试先失败**
- [x] **Step 3: 在 runner adapter 中暴露 log path / log tail 读取能力，不把文件系统路径直接泄漏给前端**
- [x] **Step 4: 在 runs application/api 层增加日志读取接口，并保持 `RunSession` 模型聚焦产品状态**
- [x] **Step 5: 将运行页右侧“错误与日志”替换为真实日志面板，保留 `last_error` 摘要**
- [x] **Step 6: 运行 `python -m unittest server.tests.test_runs_api -v`、`npm run lint`、`npm run build`**

### Task 8: Upgrade Input Assets From Single Text Box To File-Aware Inputs

**Files:**
- Modify: `server/app/models/course_draft.py`
- Modify: `server/app/application/course_drafts.py`
- Modify: `server/app/adapters/input_storage.py`
- Modify: `server/app/api/course_drafts.py`
- Modify: `server/tests/test_course_drafts_api.py`
- Modify: `web/lib/api/course-drafts.ts`
- Modify: `web/components/input/course-draft-workbench.tsx`

- [x] **Step 1: 写失败测试，覆盖多 subtitle 文件或至少文件名感知的输入存储约定**
- [x] **Step 2: 运行 `python -m unittest server.tests.test_course_drafts_api -v`，确认测试先失败**
- [x] **Step 3: 扩展 draft input storage，使输入页不再只绑定 `chapter-01.md` 单文件**
- [x] **Step 4: 在前端输入页引入文件感知输入结构，至少支持“文本输入 + 文件名/章节名”**
- [x] **Step 5: 明确 `runtime_ready` 的计算仍以真实 transcript 资产存在为准**
- [x] **Step 6: 运行 `python -m unittest server.tests.test_course_drafts_api -v`、`npm run lint`、`npm run build`**

### Task 9: Add Browser-Level Run Flow Verification

**Files:**
- Modify: `docs/runbooks/gui-dev.md`
- Optionally create: `web/tests/*` or `server/tests/*` if项目引入轻量浏览器回归脚本

- [x] **Step 1: 评估是否需要引入浏览器级回归脚本；如果没有必要，不增加新依赖**
- [x] **Step 2: 必要时使用 Playwright 做本地交互调试，验证输入 -> 配置 -> 运行 -> 结果的主链路**
- [x] **Step 3: 将浏览器调试步骤写入 `docs/runbooks/gui-dev.md`，避免只留在会话里**
- [x] **Step 4: 记录当前仍依赖人工验证的交互点和后续自动化空间**

### Task 10: Document And Verify GUI v1 Baseline

**Files:**
- Modify: `PLANS.md`
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `AGENTS.md`

- [x] **Step 1: 把剩余 GUI 批次写回 `PLANS.md`，仅保留索引、状态和验证入口**
- [x] **Step 2: 更新 GUI runbook 与 repo 规则，使运行前置条件、subcommand 契约和状态机约束可发现**
- [x] **Step 3: 运行 `python -m unittest discover -s tests -v`**
- [x] **Step 4: 运行 `python -m unittest server.tests.test_health server.tests.test_course_drafts_api server.tests.test_templates_api server.tests.test_runs_api server.tests.test_artifacts_api -v`**
- [x] **Step 5: 运行 `npm run lint` 与 `npm run build`**
- [x] **Step 6: 记录验证结果、已知缺口和下一批建议**

## Additional Completion Notes

- 已补真实 multipart 字幕文件上传，后端依赖 `python-multipart`
- 已用 Playwright 做浏览器级文件上传主链路验证
- 已补 `run.log` 增量日志流，运行页不再只依赖日志轮询预览
- 下一批如果继续做，优先级更高的是：配置预设持久化、运行历史列表、结果页搜索/过滤，而不是再扩基础运行边界
