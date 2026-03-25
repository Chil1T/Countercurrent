# `processagent` AGENTS

- 保持 `course_blueprint.json` 与 `runtime_state.json` 为运行时合同中心。
- agent 输入优先用结构化 payload，不靠自然语言上下文接力。
- 新增 stage 时，同时考虑 prompt、CLI model routing、checkpoint 语义与测试覆盖。
- `pipeline.py` 的改动必须同时检查 resume、手动 `global/*`、可选 review 与 course-scoped 输出。
- `resume-course` 必须从 `runtime_state.json` 的冻结 `run_identity` 恢复流水线身份；只能刷新 provider routing，不能借恢复路径改 `target_output`、`review_mode` 或 `review_enabled`。
- 当前单次 run 的章节循环、writer 循环和全局汇总都是串行；provider 压力评估优先基于 hosted stage 与多 run 并发，不要先发明无效并发参数。
