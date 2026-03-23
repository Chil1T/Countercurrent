# Blueprint-First Architecture

## Goal

将系统从“数据库系统概论专用脚本”升级为“任意出版教材 + 对应网课 transcript”的通用执行引擎。

## Layers

1. `Source Layer`
   - transcript
   - 用户提供的书名、目录、版次等

2. `Blueprint Layer`
   - `course_blueprint.json`
   - 描述课程、教材、章节、预期主题、输出策略

3. `Execution Layer`
   - `ingest`
   - `curriculum_anchor`
   - `gap_fill`
   - `compose_pack`
   - `review`
   - `canonicalize`

4. `Presentation Layer`
   - CLI 是当前稳定入口
   - GUI 后续只包 CLI 与 runtime files

## Operating Principles

- deterministic input 优先，AI 只补缺
- stage 之间通过结构化 JSON/Markdown 契约传递
- course runtime 不进 repo，统一落在 `out/courses/<course_id>/`
