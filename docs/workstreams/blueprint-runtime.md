# Workstream: Blueprint Runtime

## Scope

- bootstrap 课程蓝图
- 课程级 output layout
- blueprint-aware resume
- light review / conditional review

## Current Status

- 已完成 v1 runtime contract
- 已完成 agent contract v2：
  - `compose_pack` 已拆成 `pack_plan + 5 writers`
  - `canonicalize` 已拆成 `2 writers`
  - 长文本产物不再强制包进单个 JSON 返回
  - runtime 继续以 `target_output` 驱动模板差异，不新增独立 profile 持久化字段
- GUI runtime config 当前已接入真实 hosted backend 路由：
  - `provider`
  - `base_url`
  - `simple_model`
  - `complex_model`
  - `timeout_seconds`
- `timeout_seconds` 当前只控制单次 hosted LLM 请求超时，不控制整次 run 总耗时
- GUI runtime config 当前也已接入 provider policy 覆盖：
  - `max_concurrent_per_run`
  - `max_concurrent_global`
  - `max_call_attempts`
  - `max_resume_attempts`
- provider policy 当前按“内置默认值 -> config `provider_policies.<provider>` -> CLI override”解析；GUI 目前只接入前两层
- 当前主流程已切换为：
  - 默认不跑 `review`
  - `quarantine` 已移除
  - `global/*` 改为手动触发
- 当前模板会直接决定 active writers，先减少调用次数，再通过 `evidence_summary` 缩小 writer payload
- 每次 LLM 调用都会落盘到 `out/courses/<course_id>/runtime/llm_calls.jsonl`
- 同课程名当前继续复用同一 `course_id`，章节会持续追加到同一课程目录
- 当前 `resume` 已改成：
  - 锁定流水线身份：`target_output`、`review_enabled`、`review_mode`
  - 刷新 provider routing：`provider`、`base_url`、`api_key`、`simple_model`、`complex_model`、`timeout_seconds`
  - 刷新 provider policy：`max_concurrent_per_run`、`max_concurrent_global`、`max_call_attempts`、`max_resume_attempts`
- 当前章节主流程已支持“多章节并发 + 双层限流”：
  - 单 run 章节并发受 `max_concurrent_per_run` 限制
  - 全服务 provider permit 受 `max_concurrent_global` 限制
  - 单章 stage / writer 继续串行，`build-global` 继续串行
- 调用级恢复当前会对 transient HTTP 状态码与网络异常做有限重试，并把 `attempt_count`、`last_error_kind`、`retry_history` 写回 runtime；`last_error_kind` 表示最近一次失败尝试的种类，不要求最终结果仍为失败
- RunService 当前会在读取失败 run 时，对 transient 章节 run 自动触发有限次 `resume-course`；不会对 permanent failure、`clean-course` 或 provider 配置缺失后的重启失败自动恢复
- run API 当前继续保留 legacy `stages[]`，同时新增 `chapter_progress[]`；其中 `export_ready` 以当前模板/Review 所需 step 全完成为准
- artifacts export 当前支持：
  - `completed_chapters_only=true`
  - `final_outputs_only=true`
  - 两者组合时取交集
  - 严格口径 `export_ready`，不按文件是否已落盘推断 completed chapter
- 下一步可补更强的 metadata/toc 非 AI 获取，以及 GUI 级课程选择体验
