# `processagent` AGENTS

- 保持 `course_blueprint.json` 与 `runtime_state.json` 为运行时合同中心。
- agent 输入优先用结构化 payload，不靠自然语言上下文接力。
- 新增 stage 时，同时考虑 prompt、CLI model routing、checkpoint 语义与测试覆盖。
- `pipeline.py` 的改动必须同时检查章节并发调度、resume、手动 `global/*`、可选 review、retry 追责与 course-scoped 输出。
- `resume-course` 必须从 `runtime_state.json` 的冻结 `run_identity` 恢复流水线身份；只能刷新 provider routing，不能借恢复路径改 `target_output`、`review_mode` 或 `review_enabled`。
- `resume-course` 当前也允许刷新 provider policy 覆盖：`max_concurrent_per_run`、`max_concurrent_global`、`max_call_attempts`、`max_resume_attempts`；不要把它们错误归类成流水线身份。
- 当前章节主流程允许多章节并发，但单章 stage / writer 与 `build-global` 仍保持串行；并发和重试都必须先走 provider policy registry，不要绕开共享 coordination root 自行造锁。
- step 级 `attempt_count`、`last_error_kind`、`retry_history` 已经是 runtime contract；改 retry 或错误归类时，必须同时检查 `runtime_state.json`、`llm_calls.jsonl` 与 run API 映射。
- `RunService` 的自动恢复只能覆盖 transient 的章节 run，并受 `max_resume_attempts` 预算约束；`clean-course`、permanent failure、provider 配置缺失后的 restart failure 都不能自动 `resume-course`。
- export/filter 语义必须和 run API 的 `chapter_progress.export_ready` 对齐：completed chapter 只按当前 `target_output` + `review_enabled` 所需 step 全完成判断，不按 `notebooklm/*` 或中间文件是否存在判断。
- `artifacts` 导出过滤里，`completed_chapters_only` 过滤章节作用域文件，`final_outputs_only` 只保留 `chapters/<chapter_id>/notebooklm/*`；两者同时存在时取交集。
