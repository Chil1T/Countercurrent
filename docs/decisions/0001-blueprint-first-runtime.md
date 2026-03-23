# ADR 0001: Blueprint-First Runtime

## Decision

运行时课程知识框架不再硬编码在代码中，而是通过 `course_blueprint.json` 在运行时提供。

## Consequences

- pipeline 从“数据库系统概论专用”变成“教材配置驱动”
- checkpoint 必须纳入 `blueprint_hash`
- CLI 需要在运行前具备 bootstrap 能力
