# Workstream: Doc System

## Scope

- root `AGENTS.md` 作为索引
- `docs/` 作为 planner/executor 文档面
- nested `AGENTS.md` 最小化
- `docs/superpowers/` 作为 superpowers 工作产物层
- `PLANS.md` 作为执行批次索引层

## Current Status

- 文档系统主结构已稳定：`docs/` 主树 + `docs/superpowers/` 工作产物层 + `PLANS.md` 批次索引层
- GUI v1 当前状态已同步到 `AGENTS.md`、`docs/README.md`、`docs/runbooks/gui-dev.md`、`docs/runbooks/run-course.md`
- 当前入口文档已统一指向仓库内稳定路径，不再依赖某个固定 worktree 或主仓绝对路径
- 后续新增流程时，先更新对应 runbook、decision 或 workstream，再扩页面或 agent 规则

## Current Entry Points

- 用户或 Agents 查看仓库总入口：[`../../AGENTS.md`](../../AGENTS.md)
- 查看文档系统边界：[`../README.md`](../README.md)
- 查看 GUI 当前运行与验证方式：[`../runbooks/gui-dev.md`](../runbooks/gui-dev.md)
- 查看 CLI/runtime 合同：[`../runbooks/run-course.md`](../runbooks/run-course.md)
- 查看 superpowers 工作产物边界：[`../superpowers/README.md`](../superpowers/README.md)

## Operating Rules

- 正式项目知识继续落在 `architecture/`、`schemas/`、`workstreams/`、`decisions/`、`runbooks/`。
- superpowers 生成的 design/spec/implementation plan 统一落在 `docs/superpowers/`，不与正式规则文档混放。
- `PLANS.md` 只记录批次状态、范围和验证入口；详细步骤链接到 `docs/superpowers/`。
- 若某个 skill 默认使用 `context/overview/workflow/archive` 一类目录模型，应先适配本仓库 `docs/` 结构，再决定是否需要单独引入新的文档域。
- 当项目状态发生阶段性变化时，先修正入口文档的“当前基线”，再补细节文档，避免出现用户入口和 agent 入口看到不同状态。
- 当 GUI/runtime config 字段新增或语义变化时，先更新 `runbooks/gui-dev.md` 与 `runbooks/run-course.md`，把“字段做什么 / 覆盖顺序 / 生效边界 / 默认值”写清楚，再补 spec/plan 或页面文案。
