# Docs System

本目录是 `databaseleaning` 的规划者/执行者文档系统。

## Sections

- [`roadmap.md`](roadmap.md): 产品与工程阶段划分
- [`architecture/blueprint-first.md`](architecture/blueprint-first.md): 系统设计
- [`architecture/runtime-layout.md`](architecture/runtime-layout.md): 运行时布局与 checkpoint 规则
- [`schemas/course_blueprint.md`](schemas/course_blueprint.md): blueprint schema
- [`workstreams/`](workstreams): 正在推进的工作流
- [`decisions/`](decisions): ADR 风格决策记录
- [`runbooks/`](runbooks): 操作步骤
- [`runbooks/run-course.md`](runbooks/run-course.md): CLI/run/resume/clean/status 合同与操作规则
- [`runbooks/gui-dev.md`](runbooks/gui-dev.md): GUI 本地开发、浏览器验证与运行前置条件
- [`superpowers/`](superpowers): 设计稿、实施计划等 superpowers 工作产物

## Current Baseline

- `Blueprint-First Modernization` 已完成，运行时事实源仍是 `course_blueprint.json` 与 `runtime_state.json`
- `GUI Web Product v1` 已完成，当前已具备输入、配置、运行、结果四页主流程
- `Stitch V2 Frontend Migration` 已完成默认产品路由切换，当前首页、输入、配置、运行、结果与产品空态页面都使用 Stitch V2 展示层
- GUI 当前支持真实字幕文件上传、多字幕资产输入、真实 `LocalProcessRunner`、`SSE` 运行状态、`resume` / `clean`、结果树/预览/ZIP 导出、`run.log` 增量日志流
- GUI 当前已接入真实 hosted backend 路由：`provider`、`base_url`、`simple_model`、`complex_model`、`timeout_seconds`、`review_mode`、`target_output`
- 用户和 Agents 查当前 GUI 行为或配置字段语义时，优先看 [`runbooks/gui-dev.md`](runbooks/gui-dev.md) 与 [`runbooks/run-course.md`](runbooks/run-course.md)

## Principles

- repo 文档负责说明“系统该如何被改变与运行”
- `out/` 才是课程级 runtime assets 的落点
- root `AGENTS.md` 是索引，不是大杂烩
- `docs/` 主树承载正式规则；`docs/superpowers/` 承载设计与执行辅助文档
- `PLANS.md` 只做执行批次索引，不替代详细 spec/plan 文档
- 若 superpower skill 的默认文档体系与本仓库不同，应优先适配现有结构，而不是重组 `docs/`
- 涉及文档治理或 `docs/` 结构调整时，优先遵循 [`.codex/skills/databaseleaning-doc-context-ops/SKILL.md`](../.codex/skills/databaseleaning-doc-context-ops/SKILL.md)
- 当 GUI/runtime config 字段新增或语义变化时，优先同步 `runbooks/gui-dev.md` 与 `runbooks/run-course.md`，再决定是否需要补 `workstreams/` 或 root `AGENTS.md`
