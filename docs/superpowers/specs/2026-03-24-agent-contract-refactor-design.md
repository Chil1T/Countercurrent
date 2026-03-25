# Databaseleaning Agent Contract Refactor Design

**Goal:** 重构 `databaseleaning` 当前 pipeline 的 agent 输出合同，降低 hosted backend 下的 JSON 漂移风险，同时把前端三种模板真正映射到同一套 writer profile 上，而不是停留在浅层 UI 选择。

## Problem Statement

当前 pipeline 的核心风险不再是单一 provider 接线，而是 stage contract 设计不均衡：

- 多个 stage 都要求“仅输出 JSON”
- `compose_pack` 一次调用要产出 5 个 Markdown 文件，再被包装成一个 `files` JSON
- `canonicalize` 也要求把长文本结果包成 JSON
- 在 `openai_compatible` 这类 chat-completions 网关下，大 payload + 长文本 + JSON 外壳最容易发生格式漂移

实际表现已经出现：

- `compose_pack` 在 hosted backend 下返回空白或非 JSON 内容
- `parse_json_text()` 抛出 `JSONDecodeError`
- 即使 provider 通、key 通、模型通，stage contract 仍然脆

同时，前端三种模板：

- `standard-knowledge-pack`
- `lecture-deep-dive`
- `interview-focus`

目前更多只是 UI 侧选择和少量 `target_output` 映射，还没有真正下沉成 writer 级行为差异。

## Design Decision

本次重构采用：

- `结构化 stage` 保持 JSON
- `长文本产物 stage` 改为直接输出 Markdown / text
- `compose_pack` 从单次大调用改成 `pack_plan + 多个 writer`
- `canonicalize` 从单次双文本 JSON 改成两个 writer
- 三种模板统一映射到一套 `profile` 系统，而不是三套独立 pipeline

## Hard Boundaries

本次重构的硬边界不是“仅在 pipeline 中拆 step”，而是同时升级底层 LLM 输出协议：

- `LLMBackend` 必须显式区分 `generate_json()` 与 `generate_text()`
- heuristic / stub / hosted backend 都必须实现这两条 contract
- text writer 不允许退回“Markdown 再包一层 JSON”
- pipeline 只能通过这两个统一入口驱动 agent，不得引入旁路分支

如果这条边界不成立，本次重构只会把旧风险换个名字保留。

## Stage Classification

### Keep JSON Output

以下 stage 继续要求严格 JSON：

- `blueprint_builder`
- `curriculum_anchor`
- `gap_fill`
- `review`

原因：

- 输出天然是结构化对象
- 文本量相对短
- 适合 checkpoint / resume / diff
- 更适合 API 级 `json_object` 约束

### Move To Text Output

以下 stage 改为直接输出 Markdown / text：

- `compose_pack` 下的各个 writer
- `canonicalize` 下的各个 writer

原因：

- 它们的主要工作就是写长文本
- 再强套 JSON 外壳，只会增加失败面
- 在 hosted backend 下不稳定性更高

## New Compose Flow

`compose_pack` 不再作为“生成 5 文件的单一 agent”，改为：

1. `pack_plan`
   - 输出 JSON
   - 说明本章应产出哪些文件、每个文件的重点、使用哪些 transcript/topic/gap evidence
2. `write_lecture_note`
   - 输出 `01-精讲.md`
3. `write_terms`
   - 输出 `02-术语与定义.md`
4. `write_interview_qa`
   - 输出 `03-面试问答.md`
5. `write_cross_links`
   - 输出 `04-跨章关联.md`
6. `write_open_questions`
   - 输出 `05-疑点与待核.md`

### Why A Planner First

`pack_plan` 保留 JSON 的原因不是为了多一层复杂度，而是为了：

- 固定本章文件级目标
- 让后续 writer 各自只拿到局部上下文
- 让 checkpoint 粒度更可控
- 让模板 profile 的差异可以先体现在 plan，而不是散落在多个 writer prompt 里

## New Canonicalize Flow

`canonicalize` 拆成两个文本 writer：

1. `build_global_glossary`
   - 输出 `global/global_glossary.md`
2. `build_interview_index`
   - 输出 `global/interview_index.md`

这里不再要求外层 JSON：

- 每个 writer 只负责一个文本产物
- 上游 application/pipeline 直接把文本写文件

## Template Profile System

三种前端模板不做成三套独立 pipeline，而是映射到同一套 profile。

这里保持现有 runtime policy 命名空间稳定：

- 不新增独立 `profile` 字段
- 仍以 `course_blueprint.policy.target_output` 作为 runtime source of truth
- `pack_plan.writer_profile` 只是从 `target_output` 派生出的 planner/writer 视图，不是新的持久化 policy 字段

当前继续使用的 `target_output` 枚举是：

- `standard_knowledge_pack`
- `lecture_deep_dive`
- `interview_knowledge_base`

也就是说，本次重构解决的是 writer 行为和 stage contract，不同时引入新的 policy 命名空间迁移。

三种前端模板的映射为：

### `standard-knowledge-pack`

- 平衡对待 `01-精讲.md`、`02-术语与定义.md`、`03-面试问答.md`
- `write_interview_qa` 保持标准知识问答风格
- `build_interview_index` 可生成，但不强调密度

### `lecture-deep-dive`

- `write_lecture_note` 权重最高
- `write_interview_qa` 退化为课堂复盘提问，不追求面试口语化
- `write_cross_links` 更强调讲义式知识承接
- `build_interview_index` 可弱化

### `interview-focus`

- `write_terms` 与 `write_interview_qa` 权重最高
- `build_interview_index` 必须强化
- `write_lecture_note` 仍生成，但压缩为面试导向的高频概念主线

## Template Mapping Principle

模板差异应落在两层：

1. `pack_plan`
   - 决定各文件优先级、篇幅倾向和是否必须产出
2. 各 writer prompt
   - 根据 `target_output/profile` 切写作风格

模板不应导致：

- provider 分叉
- 完全不同的 runtime layout
- 三套互不兼容的 checkpoint 结构

## Conversation Shape

### Single-Turn, Context Length 2

以下 writer 适合采用“系统提示 + 单次 payload”的独立调用：

- `write_lecture_note`
- `write_terms`
- `write_interview_qa`
- `write_cross_links`
- `write_open_questions`
- `build_global_glossary`
- `build_interview_index`

原因：

- 这些任务可以通过结构化输入一次完成
- 不依赖多轮上下文记忆
- 可显著缩短单次请求上下文

### Keep Single Structured Call

以下 stage 保持现在的单次结构化调用更合理：

- `blueprint_builder`
- `curriculum_anchor`
- `gap_fill`
- `review`

原因：

- 它们天然是结构化判断任务
- 再拆成多轮对话没有明显收益

## Runtime Contract Changes

### New Step Names

原有：

- `compose_pack`
- `canonicalize`

将被细化成更小的 checkpoint：

- `pack_plan`
- `write_lecture_note`
- `write_terms`
- `write_interview_qa`
- `write_cross_links`
- `write_open_questions`
- `build_global_glossary`
- `build_interview_index`

### Checkpoint Semantics

- 每个 writer 都有自己的 step record
- 仍然受 `blueprint_hash` 和 `pipeline_signature` 约束
- 任何 profile/prompt 合同变化都应通过新的 `pipeline_signature` 失效旧 checkpoint
- `review` 必须基于五个 writer 已落盘的完整 pack 执行；任一 writer 缺失或失效时，不得复用旧 review 结果
- `build_global_glossary` / `build_interview_index` 当前采用保守失效语义：
  - 任一 chapter writer 重跑
  - 任一 chapter 被 quarantine 或重新恢复
  - active chapter 集合变化
  都会强制重建两个 global writer，避免全局产物陈旧

## Prompt Strategy

### JSON Prompts

保留“仅输出 JSON”的 prompt，但要更强调：

- 只允许单个 JSON object
- 不允许解释性前后文
- hosted backend 走 `response_format=json_object`

### Text Writer Prompts

新的 writer prompt 改成：

- 明确输出 Markdown 正文
- 不要再要求外层 JSON
- 由 pipeline/application 层决定写到哪个文件

## Validation Strategy

必须补的测试：

- `compose_pack` 拆分后的 pack plan JSON 合同测试
- 各 writer 的最小 smoke 测试
- 模板 profile 映射测试
- checkpoint / resume 对新 step 名的恢复测试
- `pipeline_signature` 变更对新 writer outputs 的失效测试

## Non-Goals

这次不做：

- per-template 独立 pipeline 分叉
- 多轮 agent memory / conversation state 持久化
- 任意 stage 间共享长对话上下文
- 复杂的 tool-calling agent framework

## Expected Outcome

完成后：

- hosted backend 下最脆弱的长文本 JSON stage 会被拆掉
- `compose_pack` 和 `canonicalize` 更容易调试与恢复
- 三种前端模板会真正体现为 writer 行为差异
- pipeline 会更适合 `openai` / `openai_compatible` / `anthropic` 的稳定调用
