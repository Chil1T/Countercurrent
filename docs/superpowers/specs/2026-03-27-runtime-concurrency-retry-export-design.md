# Runtime Concurrency / Retry / Export Design

## Goal

在不改变 `global/*` 手动汇总语义的前提下，为章节主流程引入多章节并发执行、按 provider 规则限流、临时性错误自动恢复，以及严格口径的章节级导出能力，并为后续 UI 并发态展示提供稳定合同。

## Scope

- 仅覆盖非全局章节主流程
- 新增 provider concurrency registry
- 新增调用级 transient retry 与 run 级自动 `resume`
- 扩展 `runtime_state.json` / run API / artifact export 合同
- 为 UI 增补章节级状态字段，但不在本期完成 UI 交互收口

## Non-Goals

- 不改 `build-global` 的串行执行模型
- 不做单章节内部 stage fan-out
- 不在本期完成结果页布局、文件树展开保持、并发态视觉优化
- 不引入外部任务队列、中间件或新依赖

## Current Baseline

- 当前章节主流程在 [processagent/pipeline.py](C:/Users/ming/.codex/worktrees/55a2/databaseleaning/processagent/pipeline.py) 内按 transcript 顺序串行执行。
- 当前同课程仅允许一个活跃 run，由 [server/app/application/runs.py](C:/Users/ming/.codex/worktrees/55a2/databaseleaning/server/app/application/runs.py) 拒绝并发占用同一 `course_id`。
- 当前 `resume-course` 已具备 checkpoint 复用语义，但没有自动重试调度。
- 当前导出仅支持整课 ZIP，由 [server/app/application/artifacts.py](C:/Users/ming/.codex/worktrees/55a2/databaseleaning/server/app/application/artifacts.py) 打包所有公开产物。

## Design Summary

### 1. Runtime Execution Split

将当前课程级串行 runner 拆成四层职责：

- `ChapterExecutionPlanner`
  - 基于 `course_blueprint.json`、`runtime_state.json`、当前 `target_output` 推导可执行章节与每章待执行 step。
- `ChapterWorker`
  - 负责单章节完整流水线。
  - 单章节内部仍保持 stage 串行，避免破坏现有 checkpoint 语义。
- `ProviderConcurrencyRegistry`
  - 维护 provider 默认并发、配置覆盖、单 run 并发上限、全服务 provider semaphore。
- `RetryingLLMBackend` + `AutoResumePolicy`
  - 前者处理单次 LLM 调用的 transient retry。
  - 后者处理 run 级失败后的自动 `resume-course`。

章节并发仅发生在“多章节之间”，不发生在“单章节内部”。

### 2. Provider Registry

新增 provider registry，支持：

- 内置 provider 默认项
- GUI/runtime config 覆盖
- CLI 单次运行覆盖
- 后续扩展更多 provider 或更细粒度 endpoint/model policy

首期 provider 范围：

- `openai`
- `openai_compatible`
- `anthropic`
- `heuristic`
- `stub`

建议 registry 字段：

- `max_concurrent_per_run`
- `max_concurrent_global`
- `transient_http_statuses`
- `max_call_attempts`
- `max_resume_attempts`
- `backoff_base_seconds`
- `backoff_max_seconds`
- `jitter_ratio`
- `source` (`builtin` / `config` / `cli_override`)

其中 `heuristic` / `stub` 主要提供保守默认，保持结构一致。

### 3. Retry And Resume

恢复链路分为两层：

#### 调用级 retry

封装在 LLM backend 外层，而不是散落在各 provider backend 内部。

- 默认 `max_call_attempts = 3`
- 使用指数退避 + 抖动
- 命中范围：
  - HTTP `408`
  - HTTP `409`（仅明确标记为可重试冲突时）
  - HTTP `425`
  - HTTP `429`
  - HTTP `500`
  - HTTP `502`
  - HTTP `503`
  - HTTP `504`
  - 网络超时
  - 连接重置等传输层瞬时异常

#### run 级自动 `resume`

当调用级 retry 耗尽后，若该章节/step 仍因 transient failure 失败：

- 先持久化最新 `runtime_state.json`
- 标记失败原因与章节/step 位置
- 由编排层自动再次发起 `resume-course`
- 默认 `max_resume_attempts = 2`
- `resume-course` 继续复用既有 checkpoint，仅执行未完成 step

永久性错误不进入自动 `resume`。

### 4. Runtime State Contract

保留当前 `runtime_state.json` 作为事实源，并扩展章节级与 step 级元数据。

#### Step-Level

每个 `chapters.<chapter_id>.steps.<step_name>` 增加：

- `status`: `pending` / `running` / `completed` / `failed`
- `attempt_count`
- `last_error`
- `last_error_kind`: `transient` / `permanent`
- `started_at`
- `updated_at`
- `retry_history[]`
  - `attempt`
  - `timestamp`
  - `http_status`
  - `exception_type`
  - `decision` (`retry` / `fail`)
  - `result`

#### Chapter-Level

每个章节增加聚合字段：

- `chapter_status`: `pending` / `running` / `completed` / `failed` / `partial`
- `current_step`
- `completed_step_count`
- `final_outputs_complete`
- `export_ready`
- `resume_attempt_count`

`export_ready` 采用严格口径：

- 本模板下所有 active writers 完成
- 若 `review_enabled = true`，则 `review` 也完成

### 5. Run API Contract

扩展 run 查询模型，保留当前课程级 stage 轨道，同时新增章节级实时摘要：

- `chapter_progress[]`
  - `chapter_id`
  - `status`
  - `current_step`
  - `completed_step_count`
  - `total_step_count`
  - `export_ready`
  - `retry_summary`
  - `last_error`

这样 UI 后续可以安全展示：

- 多章节同时 `running`
- 不同章节处于不同 step
- 哪些章节已可导出
- 哪些章节正在 retry / resume

### 6. Export Contract

保留原有整课导出能力，同时增加受控导出模式。

#### 保持兼容

- 继续保留 `/courses/{course_id}/export`
- 默认行为保持整课 ZIP

#### 新增过滤能力

首期支持以下过滤维度：

- `completed_chapters_only=true`
- `final_outputs_only=true`

行为定义：

- `completed_chapters_only=true`
  - 仅导出 `export_ready = true` 的章节
- `final_outputs_only=true`
  - 仅导出 `chapters/<chapter_id>/notebooklm/*`
  - 不导出 `intermediate/*`
  - 不导出 `runtime/*`
  - 不导出 `review_report.json`

可组合使用：

- 只导出已完成章节的最终产物

### 7. Concurrency Rules

首期限流采用双层控制：

- 单 run 限流
  - 限制一门课本次 run 同时运行的章节数
- 全服务 provider 限流
  - 所有 run 共享 provider 级并发池

同一 `course_id` 继续只允许一个活跃 run，避免并发写坏同一课程目录。

因此本期“并发”语义是：

- 单课内多章节并发
- 单课外仍禁止多 run 同时写同一课程
- 全局 provider 调用数仍受 provider 池约束

### 8. Testing Strategy

首期测试应覆盖：

- `PipelineRunner` / 新 orchestrator 的多章节并发调度
- checkpoint 不回退、不重复执行已完成 step
- provider registry 默认值与覆盖优先级
- transient / permanent error 判定
- 调用级 retry 次数与日志记录
- run 级自动 `resume` 次数上限
- 严格口径 `export_ready` 计算
- filtered export ZIP 内容正确性
- run API 章节级状态映射

建议最小测试集合：

- `tests.test_pipeline`
- `tests.test_cli`
- `server.tests.test_runs_api`
- `server.tests.test_artifacts_api`

必要时新增：

- `tests.test_provider_registry`
- `tests.test_retry_policy`

## Risks

- 并发执行引入新的状态竞争，尤其是 `runtime_state.json` 的写入顺序。
- 若章节 worker 与 checkpoint 更新边界不清，可能出现“文件已生成但状态未完成”或反向不一致。
- provider 限流若只落在 UI 配置而不落在 runtime contract，会导致 CLI / GUI 行为漂移。
- 自动 `resume` 若与 `RunService` 当前状态机耦合不当，可能把 orphaned run 和可恢复 run 混淆。

## Migration Notes

- 本期需要同步更新：
  - `docs/runbooks/gui-dev.md`
  - `docs/runbooks/run-course.md`
  - 必要时 `docs/workstreams/blueprint-runtime.md`
- UI 二期应直接消费新增的章节级状态字段，而不是重新扫描文件树推断完成态。

## Recommended Execution Order

1. runtime contract 与 provider registry
2. 章节并发执行器
3. 调用级 retry
4. run 级自动 `resume`
5. artifacts/export/status API 扩展
6. 文档与回归验证
