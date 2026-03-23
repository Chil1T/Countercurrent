# ADR 0002: `AGENTS.md` as Repo Index

## Decision

repo 文档系统以 root `AGENTS.md` 为索引与高层规则入口，详细文档全部下沉到 `docs/`。

## Consequences

- `AGENTS.md` 保持短小、稳定、可继承
- 特定目录约束通过最少量 nested `AGENTS.md` 处理
- planner/executor 可以从固定入口导航整个项目知识
