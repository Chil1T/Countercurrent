# GUI API Models

## Scope

本文件记录 GUI 重写所需的正式数据与接口合同，只描述：

- 主要请求/响应模型
- 字段语义
- 哪些字段已进入真实 runtime
- 哪些字段仍属于产品层

本文件不约束：

- 页面布局
- 组件组织
- 请求库实现
- 缓存策略

## Course Draft

`POST /course-drafts` 与 `GET /course-drafts/{draft_id}` 当前使用的核心模型是 `CourseDraft`。

字段：

- `id`
- `course_id`
- `book_title`
- `course_url`
- `runtime_ready`
- `detected`
- `input_slots`
- `config`

语义：

- `course_id` 由规范化后的 `book_title` 推导
- `runtime_ready` 表示当前草稿是否已经满足最小运行前置条件
- `course_url` 字段仍保留兼容，但产品界面当前已隐藏
- `config` 表示该草稿已保存的模板与运行配置

### DetectedCourseSummary

字段：

- `course_name`
- `textbook_title`
- `chapter_count`
- `asset_completeness`

语义：

- `asset_completeness` 是产品层摘要值，不直接进入 runtime contract
- `chapter_count` 表示当前已感知的输入资产数量，不保证等于 runtime 最终物化的章节总数

### InputSlot

字段：

- `kind`
- `label`
- `supported`
- `count`

语义：

- `input_slots` 当前用于表达 GUI 对输入模态的支持情况
- 某些 slot 可能仍在数据模型中保留，但不在产品界面暴露

### CreateCourseDraftRequest

字段：

- `book_title`
- `course_url`
- `subtitle_text`
- `subtitle_assets`

规则：

- `book_title` 去掉前后空格后不得为空
- `subtitle_assets` 中每项包含 `filename` 与 `content`
- `subtitle_assets` 优先于 `subtitle_text`
- 若最终规范化文件名冲突，后端返回 `409`

## Template Config

`POST /course-drafts/{draft_id}/config` 当前写入 `DraftConfig`。

### DraftConfigRequest

字段：

- `template_id`
- `content_density`
- `review_mode`
- `review_enabled`
- `export_package`
- `provider`
- `base_url`
- `simple_model`
- `complex_model`
- `timeout_seconds`

语义：

- `template_id` 决定 runtime 的 `target_output`
- `content_density` 当前属于产品层，不进入 `run-course` runtime contract
- `export_package` 当前属于产品层偏好，不进入 `run-course` runtime contract
- `provider` / `base_url` / `simple_model` / `complex_model` / `timeout_seconds` 会进入运行配置解析

### DraftConfig

字段：

- `draft_id`
- `template`
- `content_density`
- `review_mode`
- `review_enabled`
- `export_package`
- `provider`
- `base_url`
- `simple_model`
- `complex_model`
- `timeout_seconds`

## GUI Runtime Config

`GET /gui-runtime-config` 与 `PUT /gui-runtime-config` 当前读写 `GuiRuntimeConfig`。

字段：

- `default_provider`
- `providers`
- `provider_policies`

### HostedProviderSettings

字段：

- `api_key`
- `base_url`
- `simple_model`
- `complex_model`
- `timeout_seconds`

语义：

- API key 只在具体 run 子进程启动时注入环境
- 不通过修改 FastAPI 服务进程的全局环境传播 provider 密钥

### ProviderPolicySettings

字段：

- `max_concurrent_per_run`
- `max_concurrent_global`
- `max_call_attempts`
- `max_resume_attempts`

语义：

- GUI 当前只支持 provider 默认层覆盖
- 课程级 provider policy 覆盖当前不在 GUI 暴露

## Run Creation

`POST /runs` 当前使用 `CreateRunRequest`。

字段：

- `draft_id`
- `review_enabled`
- `run_kind`

语义：

- `run_kind` 取值：
  - `chapter`
  - `global`
- `review_enabled` 可作为单次 run 覆盖

## Run Session

`GET /runs/{id}`、`POST /runs/{id}/resume`、`POST /runs/{id}/clean`、SSE `run.update` 当前共享 `RunSession`。

字段：

- `id`
- `draft_id`
- `course_id`
- `created_at`
- `status`
- `run_kind`
- `backend`
- `hosted`
- `base_url`
- `simple_model`
- `complex_model`
- `timeout_seconds`
- `target_output`
- `review_enabled`
- `review_mode`
- `stages`
- `chapter_progress`
- `snapshot_complete`
- `last_error`

### RunSession Status

当前产品语义中常见状态：

- `created`
- `running`
- `failed`
- `completed`
- `cleaned`

### StageStatus

字段：

- `name`
- `status`

语义：

- `stages[]` 是 legacy 聚合阶段轨道
- 主要用于向后兼容与课程级摘要

### ChapterProgress

字段：

- `chapter_id`
- `status`
- `current_step`
- `completed_step_count`
- `total_step_count`
- `export_ready`

语义：

- `chapter_progress[]` 是章节粒度事实源
- `export_ready` 的口径是严格完成，不以文件是否存在直接推断

### snapshot_complete

语义：

- 表示该章节 run 的最终 `.md` 是否已同步到 run snapshot 层
- 主要服务于结果页 snapshot 刷新与读取

## Run Logs

### RunLogPreview

字段：

- `run_id`
- `available`
- `cursor`
- `content`
- `truncated`

### RunLogChunk

字段：

- `run_id`
- `cursor`
- `content`
- `complete`

语义：

- `GET /runs/{id}/log` 提供预览与 cursor
- `GET /runs/{id}/log/events` 提供增量日志事件

## Course Results Context

`GET /courses/{course_id}/results-context` 当前返回 `CourseResultsContext`。

字段：

- `course_id`
- `latest_run`

语义：

- `latest_run` 表示该课程当前课程级结果状态的事实源
- 结果页章节状态与加载提示优先依赖这里，而不是 scoped run 自身

## Review Summary

`GET /courses/{course_id}/review-summary` 当前返回 `ReviewSummary`。

字段：

- `course_id`
- `report_count`
- `issue_count`
- `reports`

每条 report 至少包含：

- `path`
- `status`
- `issues`

语义：

- review summary 属于结果页的摘要信息源
- review 文件本身不进入 snapshot 主树

## Results Snapshot

结果快照当前有两类只读入口：

- `GET /results-snapshot`
- `GET /courses/{course_id}/results-snapshot`

两者都返回按课程和 run 组织的最终产物快照；前者会按最新 run 时间自动选择当前课程。

### ResultsSnapshot

字段：

- `current_course_id`
- `current_course_runs`
- `historical_courses`

语义：

- `current_course_id` 可为空；当系统里还没有任何 run snapshot 时，默认结果工作台应据此渲染空的结果工作台，而不是报错
- `GET /results-snapshot` 会把最新 run 所属课程放进 `current_course_id`
- `GET /courses/{course_id}/results-snapshot` 会把请求的 `course_id` 放进 `current_course_id`

### ResultsSnapshotRun

字段：

- `run_id`
- `chapters`

### ResultsSnapshotChapter

字段：

- `chapter_id`
- `files`

### ResultsSnapshotFile

字段：

- `path`
- `kind`
- `size`

规则：

- snapshot 主树只包含最终目标 `.md`
- 中间 JSON、runtime 文件、review 文件不在主树中
- 当前课程与历史课程分开返回

`GET /courses/{course_id}/results-snapshot/content` 请求参数：

- `run_id`
- `path`
- `source_course_id`（可选）

语义：

- 用于读取 snapshot 主树中的单个最终文件
- `source_course_id` 允许读取历史课程分区中的内容

`GET /results-snapshot/content` 请求参数：

- `source_course_id`
- `run_id`
- `path`

语义：

- 用于默认 `/courses/results` 工作台读取历史课程或当前课程分区中的单个最终文件

## Export

`GET /courses/{course_id}/export` 当前支持：

- `completed_chapters_only`
- `final_outputs_only`

语义：

- 过滤规则由后端执行
- 前端不应自行重建导出口径

## Runtime-Bound Fields

当前真正进入 runtime contract 的 GUI 配置字段包括：

- `provider`
- `base_url`
- `simple_model`
- `complex_model`
- `timeout_seconds`
- `max_concurrent_per_run`
- `max_concurrent_global`
- `max_call_attempts`
- `max_resume_attempts`
- `review_enabled`
- `review_mode`
- `template -> target_output`

当前仍属于产品层、未进入 `run-course` runtime contract 的字段包括：

- `content_density`
- `export_package`

## Rewrite Baseline

若后续彻底重写 GUI，新的实现至少应继续满足：

- [`docs/workstreams/gui-product-contract.md`](../workstreams/gui-product-contract.md)
- [`docs/runbooks/gui-dev.md`](../runbooks/gui-dev.md)
- [`docs/runbooks/run-course.md`](../runbooks/run-course.md)
