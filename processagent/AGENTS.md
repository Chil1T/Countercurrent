# `processagent` AGENTS

- 保持 `course_blueprint.json` 与 `runtime_state.json` 为运行时合同中心。
- agent 输入优先用结构化 payload，不靠自然语言上下文接力。
- 新增 stage 时，同时考虑 prompt、CLI model routing、checkpoint 语义与测试覆盖。
- `pipeline.py` 的改动必须同时检查 resume、quarantine、course-scoped 输出。
