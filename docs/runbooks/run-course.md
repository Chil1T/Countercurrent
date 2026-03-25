# Runbook: Run Course

## Typical Command

```powershell
python -m processagent.cli run-course `
  --book-title "数据库系统概论" `
  --input-dir .\captions `
  --output-dir .\out `
  --toc-file .\toc.txt `
  --backend openai_compatible
```

## Resume

- 默认 `resume`
- 仅当显式传 `--clean` 时清理该课程 runtime
- GUI 配置页的“启动 / 继续运行”就是这套语义，不表示总是 fresh run
- `resume-course` 会继续同一个课程目录下已存在的 runtime，并从 `runtime_state.json` 的 `run_identity` 恢复冻结的流水线身份
- 恢复时允许刷新：
  - `provider/backend`
  - `base_url`
  - `api_key`
  - `simple_model` / `complex_model`
  - `timeout_seconds`
- 恢复时不允许改变：
  - `target_output`
  - `review_mode`
  - `review_enabled`
  - active writers / stage graph

## CLI Subcommand Contract Matrix

| Subcommand | Required | Optional | Notes |
| --- | --- | --- | --- |
| `build-blueprint` | `--book-title`, `--input-dir`, `--output-dir` | `--toc-file`, `--toc-text`, `--author`, `--edition`, `--publisher`, `--isbn`, `--backend`, stage/backend model args | 只生成 `course_blueprint.json` 和最小 `runtime_state.json` |
| `run-course` | `--book-title`, `--input-dir`, `--output-dir` | `--toc-file`, `--toc-text`, `--author`, `--edition`, `--publisher`, `--isbn`, `--backend`, model/stage model args, `--clean`, `--review-mode`, `--target-output`, `--enable-review` | GUI 章节主流程走这个命令；默认不跑 `review` |
| `resume-course` | `--book-title`, `--input-dir`, `--output-dir` | `--toc-file`, `--toc-text`, `--author`, `--edition`, `--publisher`, `--isbn`, `--backend`, `--base-url`, `--timeout-seconds`, model/stage model args, `--stub-scenario` | GUI 恢复章节运行走这个命令；只刷新 provider routing，不接受 policy override |
| `build-global` | `--book-title`, `--output-dir` | `--backend`, model/stage model args | 手动重建 `global/*`；不读取章节输入目录 |
| `clean-course` | `--book-title`, `--input-dir`, `--output-dir` | 无 | 不接受 `--backend` 或 stage model 参数 |
| `show-status` | `--book-title`, `--input-dir`, `--output-dir` | 无 | 读取 `runtime_state.json` |
| `inspect-source` | `--book-title`, `--input-dir`, `--output-dir` | 无 | 当前主要用于输入盘点 |

## Hosted Request Timeout

`--timeout-seconds` 当前的真实语义是：

- 只控制单次 hosted LLM 请求超时
- 不控制整次课程 run 总耗时
- 不影响 `heuristic` backend 的本地执行速度

默认解析顺序是：

1. CLI 显式 `--timeout-seconds`
2. 环境变量 `LLM_TIMEOUT_SECONDS`
3. CLI 默认值 `300`

GUI 侧在进入 CLI 前还会先做一层解析：

1. 课程级 `timeout_seconds`
2. provider 默认 `timeout_seconds`
3. 再回退到上面的 CLI 默认解析

非法值（例如 `<= 0`）会在 GUI/API 层直接拒绝创建 run。

## Adapter Rules

当 Web/FastAPI adapter 包装 `processagent.cli` 时，必须遵守：

- 逐个核对 subcommand 参数契约，不要假设所有子命令共享相同 flags
- GUI 的产品动作可以统一，但 CLI 参数拼装必须按具体 subcommand 分支处理
- 涉及 `run/resume/clean/status` 的 GUI 功能，先验证 `input_dir`、`output_dir` 和 `book_title` 是否能形成真实可执行命令
- 阶段状态展示以 `runtime_state.json` 和 `course_blueprint.json` 为准，不以前端本地推断为准
- `review` 当前默认关闭；只有显式传 `--enable-review` 时才会执行 reviewer
- `quarantine` 机制已移除；章节产物始终保留在 `chapters/` 下
- `global/*` 当前不是章节主流程的一部分；只通过 `build-global` 手动触发
- GUI 当前只把两类配置接入 runtime：
  - `provider/backend`
  - `base_url`
  - `simple_model` / `complex_model`
  - `timeout_seconds`
  - `template` 通过 `--target-output` 写入 blueprint `policy.target_output`
  - `review_mode` 通过 `--review-mode` 写入 blueprint `policy.review_mode`
- `content_density` 和 ZIP 导出偏好还不属于 `processagent.cli` 的运行时参数契约
- hosted API key 只允许通过单次子进程环境变量注入，不要通过修改服务进程全局环境来传播 provider 密钥
- `resume-course` 应继续同一个 run 已冻结的流水线身份；恢复时可以刷新 provider/base URL/model/timeout，但不能借恢复路径改模板或 Review 策略
- checkpoint 是否有效不能只看文件存在；当前实现还会校验 step 记录里的 pipeline signature，避免 pipeline 行为变了但旧产物被误当成可复用
- 当前 GUI/provider 配置问题，优先按 `docs/runbooks/gui-dev.md` 的 GUI 语义解释，再回到这里核对 CLI/runtime contract

## Current Stage Contract

当前 runtime contract 已拆成两类 stage：

- JSON stage
  - `blueprint_builder`
  - `curriculum_anchor`
  - `gap_fill`
  - `pack_plan`
  - `review`
- text writer stage
  - `write_lecture_note`
  - `write_terms`
  - `write_interview_qa`
  - `write_cross_links`
  - `build_global_glossary`
  - `build_interview_index`

说明：

- `pack_plan` 只负责规划，不直接输出正文
- `review` 是可选步骤，默认关闭；启用后只写 `review_report.json`，不再隔离章节
- `global/*` 由手动 `build-global` 重建，不在章节主流程自动执行
- 当前 `runtime_state.json` 会持久化：
  - `pipeline_signature`
  - provider routing 摘要
  - 冻结的 `run_identity.review_enabled`
  - 冻结的 `run_identity.review_mode`
  - 冻结的 `run_identity.target_output`
- 当前仍以 `policy.target_output` 作为 runtime 的模板 source of truth：
  - `standard_knowledge_pack`
  - `lecture_deep_dive`
  - `interview_knowledge_base`

## Writer Profile Mapping

当前模板会决定实际启用哪些 writer，而不是只改 prompt：

- `lecture_deep_dive`
  - `write_lecture_note`
  - `write_terms`
  - `write_cross_links`
- `standard_knowledge_pack`
  - `write_lecture_note`
  - `write_terms`
  - `write_interview_qa`
  - `write_cross_links`
  - `write_open_questions`
- `interview_knowledge_base`
  - `write_lecture_note`
  - `write_terms`
  - `write_interview_qa`
  - `write_cross_links`

## GUI Model Routing Mapping

GUI 当前把两层模型路由映射到 CLI/runtime 的方式是：

- `simple_model`
  - `blueprint_builder`
  - `curriculum_anchor`
  - `build_global_glossary`
  - `build_interview_index`
- `complex_model`
  - `gap_fill`
  - `pack_plan`
  - `write_lecture_note`
  - `write_terms`
  - `write_interview_qa`
  - `write_cross_links`
  - `review`

说明：

- GUI 当前仍沿用 CLI 的旧 stage model flag 名：
  - `compose_pack_model` 实际覆盖 `pack_plan + active writers`
  - `canonicalize_model` 实际覆盖 `build_global_glossary + build_interview_index`
- `build-blueprint`、`bootstrap-course` 与 `run-course` 当前都会把 `--blueprint-builder-model` 真实传给 `blueprint_builder`，不再默认回落到 provider 默认模型
- 这是兼容层，不表示 runtime 仍然存在单体 `compose_pack` 或 `canonicalize` stage

## Internal Token Accountability

每次 LLM 调用都会追加写入：

```text
out/courses/<course_id>/runtime/llm_calls.jsonl
```

每行记录至少包含：

- `course_id`
- `scope`：章节 `chapter_id` 或 `global`
- `stage`
- `provider`
- `model`
- `input_tokens`
- `output_tokens`
- `duration_ms`
- `status`
- `error`

说明：

- 这份日志只用于内部调试和追责，不面向 GUI 用户展示
- hosted backend 优先记录 provider usage；如果 provider 不返回 usage，则回退为本地估算值
- `RunService` 在后端重启后会优先从 `out/_gui/runs/<run_id>/session.json` 与 `process.log` 恢复历史日志，`/runs/{id}/log` 不再依赖 runner 进程内存快照

## Provider Pressure And Concurrency

当前单次 run 内部的执行策略是：

- transcript 章节循环：串行
- 单章内 JSON stage：串行
- 单章内 writer stage：串行
- `build-global`：串行

因此，当前最可能造成 provider 压力或额度波动的来源不是单次 run 的 fan-out，而是：

- hosted backend 下的高成本 stage：
  - `gap_fill`
  - `pack_plan`
  - active writers
  - 可选 `review`
  - 手动 `build_global_glossary` / `build_interview_index`
- 用户同时触发多个 run 或多个浏览器会话并行运行

当前结论：

- 还不需要引入 stage 级并发上限参数
- 先文档化当前串行执行 contract，并通过 `llm_calls.jsonl` 做调用追责
- 如果后续真的引入多 run 调度或 fan-out，再在 orchestration 边界增加上限控制

## Status

```powershell
python -m processagent.cli show-status `
  --book-title "数据库系统概论" `
  --input-dir .\captions `
  --output-dir .\out
```
