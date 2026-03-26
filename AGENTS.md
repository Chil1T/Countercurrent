# `databaseleaning` AGENTS

本文件是仓库级操作索引，也是项目级约束入口。

## Repo Layout

- [`.codex/skills`](.codex/skills): 仓库局部 skills；当前包含 `databaseleaning-doc-context-ops`
- [`processagent`](processagent): blueprint-first pipeline、bootstrap、CLI、prompt
- [`server`](server): FastAPI GUI 编排 API、产品模型与 adapter 边界
- [`web`](web): Next.js GUI 前端壳层与四页流程界面
- [`tests`](tests): `unittest` 回归与运行时合同测试
- [`docs`](docs): roadmap、架构、schema、决策、runbook
- [`docs/superpowers`](docs/superpowers): superpowers 生成的 spec/plan 等工作产物
- [`captions`](captions): 输入 transcript 样本
- [`out`](out): 运行时产物，不作为 repo source of truth
- [`PLANS.md`](PLANS.md): 当前执行批次索引

## Working Rules

- 优先把改动落在 runtime contract 上：`course_blueprint.json`、`runtime_state.json`、CLI 子命令。
- 给 `processagent.cli` 做 GUI / Web adapter 时，必须逐个核对 subcommand 参数契约；不要假设不同子命令共享同一组 flags。
- hosted backend 的 API key 只能按单次 subprocess run 注入环境；不要通过修改服务进程全局环境传播密钥。
- 回答或修改 GUI runtime config、backend routing、`timeout_seconds`、model routing、stage 语义前，先阅读 `docs/runbooks/gui-dev.md` 与 `docs/runbooks/run-course.md`；不要只根据前端字段名或局部实现猜语义。
- 当前 runtime 默认不跑 `review`、不使用 `quarantine`、不自动重建 `global/*`；凡是改这三条默认行为时，先更新 `docs/runbooks/run-course.md` 与 `docs/workstreams/blueprint-runtime.md`。
- 每次 LLM 调用的追责日志固定落到 `out/courses/<course_id>/runtime/llm_calls.jsonl`；这是内部调试数据，不进入用户 GUI。
- GUI 页面闭环不能替代 runtime contract 闭环；凡是涉及 `run/resume/clean/status` 的功能，先确认真实 `input_dir`、`output_dir`、`book_title` 已可执行。
- 运行页或运行 API 的状态展示，先定义状态机，再实现 UI 或事件流。
- Context 栏、运行摘要和结果页加载态应优先反映当前生效的 runtime 值；不要优先展示静态 draft 占位信息。
- `resume` 继续的是同一个 run 的冻结流水线身份：`target_output`、`review_enabled`、`review_mode` 与 stage graph 必须锁定；恢复时只重新解析当前 `provider/base_url/api_key/model/timeout`。如果要改模板或 Review 策略，请创建新的 run。
- 当 runtime/config 字段新增或语义变化时，至少同时更新 `docs/runbooks/gui-dev.md`、`docs/runbooks/run-course.md`，必要时再补 `docs/README.md` 或 `docs/workstreams/` 的当前基线。
- repo 内文档系统是 planner/executor 的操作界面；新规则优先落到 `docs/` 或最近的 `AGENTS.md`，不要散落在会话里。
- 仅在目录行为真的不同的时候添加 nested `AGENTS.md`。当前有效 nested 入口只有 `processagent/`、`tests/`、`docs/`。
- `out/` 中的课程产物默认可 resume，只有显式清理时才删除。
- `PLANS.md` 只维护执行批次索引、状态和指针；详细设计与实施计划分别落到 `docs/superpowers/specs/`、`docs/superpowers/plans/`。
- `docs/` 主树是正式项目文档；`docs/superpowers/` 是辅助工作产物层，不能替代 ADR、runbook、schema、architecture 的 source of truth。
- 除非项目明确引入独立 `context/` 文档域，否则不要把 superpower skill 里的 `context/overview/archive` 目录约定直接施加到本仓库 `docs/` 主树。
- 涉及文档系统整理、`AGENTS.md`/`docs/` 结构调整、spec/plan 落点治理时，先阅读并遵循仓库局部 skill：`.codex/skills/databaseleaning-doc-context-ops/SKILL.md`。
- 涉及本地前后端服务的启动、停止、重启、探活时，先阅读 `docs/runbooks/gui-dev.md` 的 `Service Lifecycle`；不要把“命令执行了”误判成“服务已就绪”。

## Commands

- 环境变量加载与 CLI: `python -m processagent.cli <subcommand> ...`
- 全量测试: `python -m unittest discover -s tests -v`
- GUI backend tests: `python -m unittest server.tests.test_health server.tests.test_course_drafts_api server.tests.test_templates_api server.tests.test_runs_api server.tests.test_artifacts_api -v`
- GUI frontend lint: `npm run lint` in `web/`
- GUI frontend build: `npm run build` in `web/`
- 常用子命令:
  - `build-blueprint`
  - `run-course`
  - `resume-course`
  - `clean-course`
  - `show-status`

## Doc Index

- [`docs/README.md`](docs/README.md): 文档系统总览与当前基线
- [`docs/superpowers/README.md`](docs/superpowers/README.md): superpowers 文档层边界与兼容规则
- [`.codex/skills/databaseleaning-doc-context-ops/SKILL.md`](.codex/skills/databaseleaning-doc-context-ops/SKILL.md): 仓库局部文档治理 skill
- [`docs/roadmap.md`](docs/roadmap.md): 分阶段 roadmap
- [`docs/architecture/blueprint-first.md`](docs/architecture/blueprint-first.md): 运行时架构
- [`docs/architecture/runtime-layout.md`](docs/architecture/runtime-layout.md): `out/` 布局与 checkpoint
- [`docs/schemas/course_blueprint.md`](docs/schemas/course_blueprint.md): blueprint schema
- [`docs/workstreams/blueprint-runtime.md`](docs/workstreams/blueprint-runtime.md): 当前主工作流
- [`docs/workstreams/doc-system.md`](docs/workstreams/doc-system.md): 文档系统工作流与当前状态
- [`docs/decisions/0001-blueprint-first-runtime.md`](docs/decisions/0001-blueprint-first-runtime.md): 关键决策
- [`docs/runbooks/bootstrap-course.md`](docs/runbooks/bootstrap-course.md): bootstrap runbook
- [`docs/runbooks/gui-dev.md`](docs/runbooks/gui-dev.md): GUI 本地开发与验证
- [`docs/runbooks/run-course.md`](docs/runbooks/run-course.md): 执行 runbook

## Done Means

- 行为变更已落到代码、测试和相关文档
- `python -m unittest discover -s tests -v` 通过
- 如新增规则或协作约束，已更新最近的 `AGENTS.md` 或 `docs/`
