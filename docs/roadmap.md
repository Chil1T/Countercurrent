# Roadmap

## Phase 1: Blueprint Runtime

- 引入 `course_blueprint.json`
- 引入 `runtime_state.json`
- 输出迁移到 `out/courses/<course_id>/...`
- resume 改为 blueprint-aware

## Phase 2: CLI-first Operations

- 子命令化 CLI
- stage-specific model routing
- `build-blueprint` / `run-course` / `show-status`

## Phase 3: Repo Doc System

- root `AGENTS.md` 成为索引
- `docs/` 承载架构、schema、runbook、decision
- nested `AGENTS.md` 只保留最小集合

## Phase 4: GUI Web Product v1

- GUI 只包裹 CLI 与 runtime contracts
- 不引入第二套执行路径
- 已完成输入、配置、运行、结果四页主流程
- 已完成真实字幕文件上传、`LocalProcessRunner`、`SSE` 状态流、结果预览与 ZIP 导出

## Next

- 配置预设持久化
- 运行历史列表
- 结果页搜索 / 过滤
## Deferred

- `uploaded_material` 多模态教材
- embedding / RAG
- 更丰富的非 AI 书目信息获取
