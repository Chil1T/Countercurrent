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
- 当前单次 run 的章节循环、writer 循环和手动 `global/*` 汇总都是串行；provider 压力主要来自 hosted stage 成本与多 run 并发，而不是单 run fan-out
- 下一步可补更强的 metadata/toc 非 AI 获取，以及 GUI 级课程选择体验
