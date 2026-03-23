# `databaseleaning` AGENTS

本文件是仓库级操作索引，也是项目级约束入口。

## Repo Layout

- [`processagent`](/C:/Users/ming/Documents/databaseleaning/processagent): blueprint-first pipeline、bootstrap、CLI、prompt
- [`tests`](/C:/Users/ming/Documents/databaseleaning/tests): `unittest` 回归与运行时合同测试
- [`docs`](/C:/Users/ming/Documents/databaseleaning/docs): roadmap、架构、schema、决策、runbook
- [`captions`](/C:/Users/ming/Documents/databaseleaning/captions): 输入 transcript 样本
- [`out`](/C:/Users/ming/Documents/databaseleaning/out): 运行时产物，不作为 repo source of truth
- [`PLANS.md`](/C:/Users/ming/Documents/databaseleaning/PLANS.md): 当前执行批次索引

## Working Rules

- 优先把改动落在 runtime contract 上：`course_blueprint.json`、`runtime_state.json`、CLI 子命令。
- repo 内文档系统是 planner/executor 的操作界面；新规则优先落到 `docs/` 或最近的 `AGENTS.md`，不要散落在会话里。
- 仅在目录行为真的不同的时候添加 nested `AGENTS.md`。当前有效 nested 入口只有 `processagent/`、`tests/`、`docs/`。
- `out/` 中的课程产物默认可 resume，只有显式清理时才删除。

## Commands

- 环境变量加载与 CLI: `python -m processagent.cli <subcommand> ...`
- 全量测试: `python -m unittest discover -s tests -v`
- 常用子命令:
  - `build-blueprint`
  - `run-course`
  - `resume-course`
  - `clean-course`
  - `show-status`

## Doc Index

- [`docs/README.md`](/C:/Users/ming/Documents/databaseleaning/docs/README.md): 文档系统总览
- [`docs/roadmap.md`](/C:/Users/ming/Documents/databaseleaning/docs/roadmap.md): 分阶段 roadmap
- [`docs/architecture/blueprint-first.md`](/C:/Users/ming/Documents/databaseleaning/docs/architecture/blueprint-first.md): 运行时架构
- [`docs/architecture/runtime-layout.md`](/C:/Users/ming/Documents/databaseleaning/docs/architecture/runtime-layout.md): `out/` 布局与 checkpoint
- [`docs/schemas/course_blueprint.md`](/C:/Users/ming/Documents/databaseleaning/docs/schemas/course_blueprint.md): blueprint schema
- [`docs/workstreams/blueprint-runtime.md`](/C:/Users/ming/Documents/databaseleaning/docs/workstreams/blueprint-runtime.md): 当前主工作流
- [`docs/workstreams/doc-system.md`](/C:/Users/ming/Documents/databaseleaning/docs/workstreams/doc-system.md): 文档系统工作流
- [`docs/decisions/0001-blueprint-first-runtime.md`](/C:/Users/ming/Documents/databaseleaning/docs/decisions/0001-blueprint-first-runtime.md): 关键决策
- [`docs/runbooks/bootstrap-course.md`](/C:/Users/ming/Documents/databaseleaning/docs/runbooks/bootstrap-course.md): bootstrap runbook
- [`docs/runbooks/run-course.md`](/C:/Users/ming/Documents/databaseleaning/docs/runbooks/run-course.md): 执行 runbook

## Done Means

- 行为变更已落到代码、测试和相关文档
- `python -m unittest discover -s tests -v` 通过
- 如新增规则或协作约束，已更新最近的 `AGENTS.md` 或 `docs/`
