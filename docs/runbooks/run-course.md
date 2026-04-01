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
- 课程目录解析会先规范化 `book_title`（去掉前后空格）再生成 `course_id`；`build-global` / `resume-course` / `show-status` / `clean-course` 都按这条规则查已有课程
- 无 TOC 时，`blueprint_builder` 只补章节结构；`course_name` 会继续锚定用户输入的 `book_title`，避免 LLM 改写标题后把 GUI/CLI 指向不同的 `course_id`
- 新的 `run-course` 如果复用已有课程目录，会用当前配置重写 `runtime_state.run_identity`；只有 `resume-course` 才会显式沿用已冻结的流水线身份
- 恢复时允许刷新：
  - `provider/backend`
  - `base_url`
  - `api_key`
  - `simple_model` / `complex_model`
  - `timeout_seconds`
  - `max_concurrent_per_run`
  - `max_concurrent_global`
  - `max_call_attempts`
  - `max_resume_attempts`
- 恢复时不允许改变：
  - `target_output`
  - `review_mode`
  - `review_enabled`
  - active writers / stage graph

## CLI Subcommand Contract Matrix

| Subcommand | Required | Optional | Notes |
| --- | --- | --- | --- |
| `build-blueprint` | `--book-title`, `--input-dir`, `--output-dir` | `--toc-file`, `--toc-text`, `--author`, `--edition`, `--publisher`, `--isbn`, `--backend`, stage/backend model args | 只生成 `course_blueprint.json` 和最小 `runtime_state.json` |
| `run-course` | `--book-title`, `--input-dir`, `--output-dir` | `--toc-file`, `--toc-text`, `--author`, `--edition`, `--publisher`, `--isbn`, `--backend`, model/stage model args, `--clean`, `--review-mode`, `--target-output`, `--enable-review`, `--run-id`, provider policy args（`--max-concurrent-per-run` / `--max-concurrent-global` / `--max-call-attempts` / `--max-resume-attempts`） | GUI 章节主流程走这个命令；默认不跑 `review`；若提供 `--run-id`，会同步最终 `.md` 到该 run 的 snapshot 目录 |
| `resume-course` | `--book-title`, `--input-dir`, `--output-dir` | `--toc-file`, `--toc-text`, `--author`, `--edition`, `--publisher`, `--isbn`, `--backend`, `--base-url`, `--timeout-seconds`, model/stage model args, `--stub-scenario`, `--run-id`, provider policy args（`--max-concurrent-per-run` / `--max-concurrent-global` / `--max-call-attempts` / `--max-resume-attempts`） | GUI 恢复章节运行走这个命令；刷新 provider routing 与 provider policy，但不接受 pipeline identity override；若提供 `--run-id`，会继续刷新该 run 的 snapshot |
| `build-global` | `--book-title`, `--output-dir` | `--backend`, model/stage model args, provider policy args（`--max-concurrent-per-run` / `--max-concurrent-global` / `--max-call-attempts` / `--max-resume-attempts`） | 手动重建 `global/*`；不读取章节输入目录 |
| `clean-course` | `--book-title`, `--input-dir`, `--output-dir` | `--run-id` | 不接受 `--backend` 或 stage model 参数；若提供 `--run-id`，会额外删除该 run 在 `results-snapshots/` 下的最终产物快照 |
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

## Provider Policy And Recovery

当前 provider policy 合同包括：

- `max_concurrent_per_run`：单 run 章节并发上限
- `max_concurrent_global`：全服务 provider permit 上限
- `max_call_attempts`：单次 hosted LLM 调用最大重试次数
- `max_resume_attempts`：run 级自动 `resume-course` 最大次数

内置默认值当前覆盖：

- `openai`
- `openai_compatible`
- `anthropic`
- `heuristic`
- `stub`

解析顺序当前是：

1. provider 内置默认值
2. config 层 `provider_policies.<provider>` 覆盖
3. `run-course` / `resume-course` / `build-global` 显式 flags 覆盖

说明：

- GUI 当前只接入第 1/2 层，不提供课程级 provider policy override
- 非法值（例如布尔值、字符串整数、`<= 0`）应在配置解析或参数校验阶段直接拒绝

恢复策略当前分两层：

- 调用级：对 transient HTTP 状态码 `408`、`425`、`429`、`500`、`502`、`503`、`504` 与网络异常做有限重试
- run 级：GUI / `RunService` 在读取失败的章节 run 时，可在 `max_resume_attempts` 预算内自动触发 `resume-course`

追责落点当前包括：

- `runtime_state.json`
  - `attempt_count`：该 step 实际发起的调用次数
  - `last_error_kind`：最近一次失败尝试的错误类型；即使最终尝试成功，也可能保留最后一次 transient error
  - `retry_history`：按尝试顺序记录每次 error/completed，以及该次失败后是否继续重试
- `out/courses/<course_id>/runtime/llm_calls.jsonl`

自动 `resume-course` 的边界当前是：

- 只针对 `run_kind = chapter` 的失败 run
- 只针对 `runtime_state.last_error_kind` 仍被识别为 transient 的失败
- 要求当前 provider 配置仍可解析，且 `auto_resume_attempt_count < max_resume_attempts`
- 不覆盖 `clean-course`
- 不覆盖 permanent failure
- 不覆盖服务重启后 provider 配置缺失导致的失败

## Adapter Rules

当 Web/FastAPI adapter 包装 `processagent.cli` 时，必须遵守：

- 逐个核对 subcommand 参数契约，不要假设所有子命令共享相同 flags
- GUI 的产品动作可以统一，但 CLI 参数拼装必须按具体 subcommand 分支处理
- 涉及 `run/resume/clean/status` 的 GUI 功能，先验证 `input_dir`、`output_dir` 和 `book_title` 是否能形成真实可执行命令
- 阶段状态展示以 `runtime_state.json` 和 `course_blueprint.json` 为准，不以前端本地推断为准
- `review` 当前默认关闭；只有显式传 `--enable-review` 时才会执行 reviewer
- `quarantine` 机制已移除；章节产物始终保留在 `chapters/` 下
- `global/*` 当前不是章节主流程的一部分；只通过 `build-global` 手动触发
- `build-global` 不会改写已冻结的 `runtime_state.run_identity`；它只重建 `global/*`，不会把原先章节 run 的 `review_enabled / review_mode / target_output` 改成当前临时配置
- `build-global` 汇总章节时，优先以当前 `runtime_state.json` 里的章节 scope 作为输入集合；只有其关键 writer step 仍匹配当前 `blueprint_hash` 的 scope 才会被视为活跃章节，旧 run 遗留 scope 或目录不会再混入全局术语表或面试索引
- 对同一个 `course_id`，当前 orchestration 只允许一个活跃 run；无论章节主流程还是 `build-global`，如果已有 `running` run 占用同一课程输出目录，就应先拒绝新 run，避免并发写坏 `runtime_state.json` 和 checkpoint
- GUI 当前会把以下配置接入 runtime：
  - `provider/backend`
  - `base_url`
  - `simple_model` / `complex_model`
  - `timeout_seconds`
  - provider 级 `provider_policies.*`
  - `template` 通过 `--target-output` 写入 blueprint `policy.target_output`
  - `review_mode` 通过 `--review-mode` 写入 blueprint `policy.review_mode`
- `content_density` 和 ZIP 导出偏好还不属于 `processagent.cli` 的运行时参数契约
- hosted API key 只允许通过单次子进程环境变量注入，不要通过修改服务进程全局环境来传播 provider 密钥
- `resume-course` 应继续同一个 run 已冻结的流水线身份；恢复时可以刷新 provider/base URL/model/timeout 与 provider policy，但不能借恢复路径改模板或 Review 策略
- 当 GUI 草稿还没有保存课程模板配置时，运行时默认按 `interview_knowledge_base` 解释 active writers 与阶段轨道，保持和 pipeline blueprint 默认值一致
- checkpoint 是否有效不能只看文件存在；当前实现还会校验 step 记录里的 pipeline signature，避免 pipeline 行为变了但旧产物被误当成可复用
- 当前 GUI/provider 配置问题，优先按 `docs/runbooks/gui-dev.md` 的 GUI 语义解释，再回到这里核对 CLI/runtime contract
- 对 GUI draft 输入，字幕文件名在规范化后必须唯一；如果两个上传项最终会写到同一个 `input/<filename>.md`，adapter 应拒绝而不是静默覆盖
- chapter/export 状态必须以 runtime step 完成态为准，不要用 `notebooklm/*` 或中间文件是否存在来推断 completed chapter

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
  - step 级 `attempt_count`
  - step 级 `last_error_kind`
  - step 级 `retry_history`
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
- 对 `clean-course`，如果后端在清理过程中重启且 runner snapshot 丢失，`RunService` 会根据课程 runtime 目录是否仍存在来恢复 `cleaned` 终态，避免状态永久卡在 `running`
- 对普通章节 run 或 `build-global`，如果服务重启后 runner snapshot 丢失、runtime 也尚未达到完成态且没有显式 `last_error`，`RunService` 会把该 run 判成失败并附带 orphaned-run 错误说明，避免旧的 `running` 记录永久占住同一个 `course_id`

## Provider Pressure And Concurrency

当前单次 run 内部的执行策略是：

- transcript 章节循环：按 provider policy 限定的多章节并发
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

- 章节级并发只发生在多章之间，不发生在单章内部
- 单 run 并发与全服务 provider 并发都必须受 provider policy registry 控制
- `llm_calls.jsonl` 与 `runtime_state.json` 共同承担调用追责与重试审计
- 如果后续真的引入 stage 级 fan-out，再在当前 registry 之上扩展，而不是绕开现有 coordination root

## Run API Contract

`GET /runs/{id}` 对章节 run 当前同时暴露两层合同：

- `stages[]`：向后兼容的聚合阶段轨道
- `chapter_progress[]`：章节粒度进度，用于并发运行态与结果页

`chapter_progress[]` 的每个元素当前包含：

- `chapter_id`
- `status`：`pending` / `running` / `completed` / `failed`
- `current_step`：当前 running 或 failed 的 step；章节已 completed 时为 `null`
- `completed_step_count`
- `total_step_count`
- `export_ready`

其中 `export_ready` 的严格口径是：

- 仅当当前 `target_output` + `review_enabled` 所要求的全部章节 step 都已 `completed` 时为 `true`
- 章节目录里存在 `notebooklm/*` 或部分中间文件，不足以把该章视为 completed
- `GET /runs/{id}` 如果触发了自动 `resume-course`，返回值可能直接从 `failed` 翻回 `running`

## Artifacts Export Contract

`GET /courses/{course_id}/export` 当前支持以下过滤参数：

- `completed_chapters_only=true`
- `final_outputs_only=true`

语义是：

- `completed_chapters_only=true`：仅保留 `export_ready` 章节的章节作用域文件；课程根文件和非章节文件继续保留
- `final_outputs_only=true`：仅保留 `chapters/<chapter_id>/notebooklm/*`
- 两者同时为 `true`：只保留“严格 completed chapter”的 `notebooklm/*`

## Results Snapshot Contract

GUI 当前新增只读快照层，用于支撑默认结果工作台的最终产物树：

```text
out/_gui/results-snapshots/<course_id>/<run_id>/chapters/<chapter_id>/notebooklm/*.md
```

说明：

- snapshot 只保存最终目标 `.md`
- snapshot 不包含 `intermediate/*.json`、`runtime/*`、`review_report.json`
- `run-course` / `resume-course` 只有在提供 `--run-id` 时才会同步该层
- `build-global` 不写入 snapshot 主树；`global/*` 仍留在兼容 artifacts/export 路径
- `clean-course --run-id <id>` 会删除该 run 在 `results-snapshots/` 下的快照目录
- 结果页当前主树以 snapshot 为事实源；旧 `artifacts/*` 仍用于兼容导出和其他非主树读取路径

## Status

```powershell
python -m processagent.cli show-status `
  --book-title "数据库系统概论" `
  --input-dir .\captions `
  --output-dir .\out
```
