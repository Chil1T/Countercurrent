# Runtime Layout

## Directory Shape

```text
out/
  courses/
    <course_id>/
      course_blueprint.json
      runtime_state.json
      chapters/
        <chapter_id>/
          intermediate/
            normalized_transcript.json
            topic_anchor_map.json
            augmentation_candidates.json
          notebooklm/
            01-精讲.md
            02-术语与定义.md
            03-面试问答.md
            04-跨章关联.md
            05-疑点与待核.md
          review_report.json
      global/
        global_glossary.md
        interview_index.md
      runtime/
        llm_calls.jsonl
```

## Checkpoint Rules

- `ingest` 仅依赖 transcript 本身，通常可跨 blueprint 变化复用
- 其余 step 依赖 `blueprint_hash`
- 当 `blueprint_hash` 不一致时，下游 step 自动失效
- 默认 `resume`
- 显式 `clean-course` 或 `--clean` 才删除运行时产物
- `global/*` 仅在手动 `build-global` 时重建
- `review` 当前是可选步骤，不再驱动章节隔离

## Runtime State

`runtime_state.json` 记录：

- `course_id`
- `blueprint_hash`
- `provider`
- `default_model`
- `stage_models`
- `chapters.<chapter_id>.steps.*`
- `global.build_global_glossary`
- `global.build_interview_index`
- `last_error`
