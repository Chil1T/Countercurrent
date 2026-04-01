# Run / Results Snapshot-Driven Design

> Status: proposed  
> Owner: Codex  
> Date: 2026-04-01

## Summary

本轮重新定义 `Run` 与 `Results` 的默认产品语义，不再沿用“空态页 + 当前课程目录树”的旧组织方式。

新的目标是：

- `Run` 页面不再有单独空态页；没有真实 run 时也渲染完整工作台，只是在进度和状态区标明“任务未开始”
- `Results` 页面不再展示中间件与运行文件，只展示目标最终 `.md`
- 为了让结果页可以真正按 `course_id -> run_id -> md` 组织，需要引入新的最终产物快照合同：
  - `out/_gui/results-snapshots/<course_id>/<run_id>/chapters/<chapter_id>/notebooklm/*.md`
- 结果页文件树改成：
  - `过去课程产物`
  - `当前课程产物`
  - 当前课程下再按 `run_id` 分组，并标出 `当前 run`

这不是单纯的前端重排，而是一次“产品信息架构 + 运行产物持久化合同”的联合调整。

## Superseded Contracts

如果本 spec 被采纳并进入实现，它会显式替换下面这些当前冻结合同：

- `/runs` 作为产品空态页的语义
- `/courses/results` 作为产品空态页的语义
- 结果页默认由 `course-level latest run + scoped run 仅标签 + public artifact tree` 驱动的语义

也就是说，这不是对现有 Stitch V2 高保真计划的局部补丁，而是对其中 `Run / Results` 页面合同的后续 supersede。

在代码尚未实现之前，当前正式 source of truth 仍然是：

- `docs/runbooks/gui-dev.md`
- `docs/runbooks/run-course.md`
- 现有 `Run / Results V2` 路由与组件实现

只有在本 spec 对应实现落地并同步更新 runbook 后，上述旧合同才算被真正替换。

## Why Change

当前系统虽然保留了历史 `course_id` 目录和 GUI `run_id` 会话，但最终目标 `.md` 产物仍然只落在：

- `out/courses/<course_id>/chapters/<chapter_id>/notebooklm/*.md`

这导致两个问题：

1. 同一 `course_id` 下没有独立的 `run_id` 最终产物快照，结果页无法可靠展示历史 run 的最终 `.md`
2. 结果页当前文件树仍然以课程目录扫描为主，会把 `intermediate/`、runtime、review 等内部文件混进结果浏览体验

如果继续只改前端，不补 run-level snapshot，结果页就只能“猜”历史 run 内容，语义不稳。

另外，snapshot 不能直接放在 `out/courses/<course_id>/runs/<run_id>/notebooklm/*.md` 这种平面结构里，因为每章 writer 的最终文件名集合是固定的，同一 run 下多章会互相覆盖；它也不能继续放在 `course_dir` 里，否则会和当前 `clean-course` 删除课程目录的合同直接冲突。

## Goals

- 取消 `Run` 和 `Results` 的专门空态页
- 让 `Run` 在没有 run 时也能以完整工作台方式渲染
- 为每次章节 run 引入 run-level 最终产物快照，只保存目标 `.md`
- 让 `Results` 文件树只展示最终目标 `.md`
- 让 `Results` 能按 `course_id -> run_id -> md` 稳定组织和展示
- 在当前课程产物内清晰标识 `当前 run`

## Non-Goals

- 不重做章节并发、retry、export 的 backend 主合同
- 不恢复 `intermediate/` 或 runtime 文件到结果页主树
- 不把 review 报告重新塞回结果树主体
- 不改变 preview 仅内部调试的边界
- 不要求为 `global/*` 设计新的主展示区；本轮优先聚焦章节最终 `.md`

## Current Facts

### Existing Contracts

- 历史课程目录按 `course_id` 保留在 `out/courses/<course_id>/...`
- 同课程名当前继续复用同一 `course_id`
- GUI `run_id` 会话会持久化到 `out/_gui/runs/<run_id>/session.json`
- 同一 `course_id` 下当前只允许一个活跃 run

### Existing Gaps

- 同一 `course_id` 下没有 `run_id` 级别的最终 `.md` 快照目录
- 结果树当前仍是“课程目录扫描”的公共 artifact 树，而不是“最终学习产物树”
- `Run` / `Results` 仍保留了专门的空态路由语义

## New Storage Contract

### Course Final Outputs Remain

课程主目录仍继续保留当前最终产物位置：

```text
out/
  courses/
    <course_id>/
      chapters/
        <chapter_id>/
          notebooklm/
            *.md
```

### New Run Snapshot Layer

每次章节 run 完成后，新增只读快照目录：

```text
out/
  _gui/
    results-snapshots/
      <course_id>/
        <run_id>/
          chapters/
            <chapter_id>/
              notebooklm/
                *.md
```

规则：

- 只保存最终目标 `.md`
- 不保存 `intermediate/*.json`
- 不保存 `runtime/llm_calls.jsonl`
- 不保存 `review_report.json`
- 允许覆盖同一 `run_id + chapter_id` 下同名快照文件，但不同 `run_id` 彼此隔离
- snapshot 物理位置与课程主目录解耦，不受 `clean-course` 删除 `course_dir` 的影响

### Snapshot Lifecycle

为避免 snapshot 与 runtime 身份分叉，本轮把生命周期明确成下面几条：

- `fresh run`
  - 创建新的 `run_id`
  - 初始化空的 `out/_gui/results-snapshots/<course_id>/<run_id>/chapters/`
  - 不影响历史 `run_id` 快照
- `resume same run`
  - 继续写入同一个 `run_id` 快照目录
  - 已存在同名 `.md` 可被覆盖
  - 不新建第二份 snapshot
- `same course, new run`
  - 新建新的 `run_id` snapshot 目录
  - 历史 `run_id` snapshot 保留，供结果页按 run 维度查看
- `chapter rerun inside same run`
  - 对应章节最终 `.md` 在当前 `run_id` 目录内覆盖更新
- `running / failed`
  - snapshot 允许处于“部分完成”状态
  - 结果页可显示已完成章节对应的 `.md`
  - run 元数据必须显式标明该 snapshot 是否完整
- `clean-course`
  - 删除当前 `run_id` snapshot 目录
  - 历史其他 `run_id` snapshot 不受影响

换句话说，snapshot 不是“只在整次 run 成功时一次性落盘”，而是“随章节完成递增写入，并由 run 状态标识是否完整”。

## Run Page Redesign

### No More Empty Route Semantics

`/runs` 不再作为“空态页”；它变成“当前未绑定 run 时的默认运行工作台”。

### New Default States

页面状态改成：

- `任务未开始`
- `进行中`
- `已完成`
- `失败`
- `已清理`

### Unstarted Behavior

当没有真实 `run_id` 时：

- 仍然渲染完整 Run 工作台
- 章节卡片、状态栏、日志区都显示“未开始”状态
- 不伪造 runtime 数据
- 所有需要真实 run 的动作要禁用或引导回配置页发起运行

这样用户即使还没启动 run，也能看到完整的运行界面结构，而不是进入另一套空态页。

### Unstarted Read Model

为避免“没有 run 但又要渲染 Run 工作台”时组件失去合法数据源，本轮明确引入未开始态 read model：

- 页面不再要求必须有真实 `RunSession`
- 当 URL 只有 `/runs` 时，前端读取当前 shell context 中可用的：
  - `draftId`
  - `courseId`
  - 已保存模板配置
  - 已保存 AI 服务配置
  - 已上传章节资产数量
- 这些数据被组装成一个 `UnstartedRunWorkbenchState`

它只提供：

- 计划运行的课程名 / `course_id`
- 目标模板与 `target_output`
- provider / model 摘要
- 章节数量或待处理资产数量
- 所有 run-only 动作的禁用态

它不提供：

- 虚构的 `RunSession.id`
- 虚构的日志内容
- 虚构的 SSE 状态

因此 `/runs` 渲染的是“未开始工作台”，不是“伪造中的运行态”。

### GUI Run Identity To Runtime

因为 snapshot 必须按 GUI `run_id` 落盘，本轮同时要求把 `run_id` 从 GUI 编排层显式传进 CLI/runtime：

- `CourseRunSpec` 增加 `run_id` 的 runtime 透传字段
- `processagent.cli` 为 `run-course`、`resume-course`、`clean-course` 增加可选 `--run-id`
- `PipelineConfig` / `PipelineRunner` 接收该 `run_id`

这样 snapshot 写入点才能和 GUI session 身份对齐，而不是靠目录猜测。

## Results Page Redesign

### No More Empty Route Semantics

`/courses/results` 不再作为“空态页”；它变成“默认结果工作台”。

### Target-MD Only Tree

结果页主树只展示目标最终 `.md`，不再显示：

- `intermediate/`
- `runtime/*`
- `review_report.json`
- 其他非目标最终学习产物文件

### New Tree Structure

结果树改成：

```text
过去课程产物
  <course_id>
    <run_id>
      <chapter_id>
        *.md

当前课程产物
  <run_id>
    <chapter_id>
      *.md
```

其中：

- `过去课程产物` 指当前课程之外的其他 `course_id`
- `当前课程产物` 指当前页面绑定的 `course_id`
- 在当前课程产物下，如果页面带 `runId`，则对对应分组标记 `当前 run`

### Preview Pane

预览面板继续显示当前选中的 `.md` 内容，但来源切换成 run snapshot 或当前课程最终 `.md` 集合，而不是旧的公共 artifact 树。

### Source Of Truth

本轮需要明确结果页到底信谁：

- `results-snapshot` read model
  - 成为结果页主树的唯一 source of truth
  - 负责 `course_id -> run_id -> md` 的树结构、当前 run 标记、run 完整度
- 现有 `public artifact tree`
  - 继续保留给兼容路径、旧测试、以及非结果工作台使用
  - 不再作为默认结果页主树的数据源

这意味着“结果页只显示最终 `.md`”和“现有 artifacts API 仍兼容”可以同时成立，但角色不同：

- `results-snapshot` 负责默认结果页树
- `artifacts/*` 负责兼容与其他功能，不再驱动默认树

## API / Reader Contract Changes

为了支持新的结果页语义，本轮建议不要继续用旧的 “public artifact tree” 直接驱动页面，而是补一个更明确的结果快照读取合同。

### Keep Existing APIs

以下 API 保持兼容：

- `GET /courses/{course_id}/artifacts/tree`
- `GET /courses/{course_id}/artifacts/content`
- `GET /courses/{course_id}/review-summary`
- `GET /courses/{course_id}/export`

### Add Snapshot-Aware Read API

新增一类面向结果工作台的 read model，例如：

- `GET /courses/{course_id}/results-snapshot`
- `GET /courses/{course_id}/results-snapshot/content`

返回：

- `current_course_id`
- `current_run_id`
- `historical_courses[]`
- `current_course_runs[]`
- 每个 run 下的最终 `.md` 文件列表
- 每个 run 的 `status`
- 每个 run 的 `snapshot_complete`

这类 read API 只描述“结果工作台需要的最终学习产物树”，不暴露中间产物。

说明：

- `review-summary` 继续使用现有课程级 contract，不转移到 snapshot API
- 导出过滤当前仍使用现有 `export` contract，以课程主目录 `chapters/*/notebooklm/*` 为事实源
- 结果页主树与导出事实源暂时允许分离：前者看 run snapshot，后者看课程最终产物
- 如果后续需要“按 run 导出”，再单独扩展，不在本轮一并引入
- `results-snapshot/content` 必须支持读取“过去课程产物”里的文件，因此它不能只隐式绑定当前页面 `course_id`
  - 建议最小参数集为：`source_course_id`、`run_id`、`path`

## Snapshot Creation Timing

run-level snapshot 需要在章节达到 `export_ready` 时增量生成，而不是等整次 run 结束后一次性生成。

建议行为：

- 章节达到 `export_ready` 时，从当前 `chapters/*/notebooklm/*.md` 复制对应最终 `.md`
- 写入 `out/_gui/results-snapshots/<course_id>/<run_id>/chapters/<chapter_id>/notebooklm/*.md`
- 同一次 run 中，如果同一章节最终产物被重写，则覆盖当前 `run_id` 目录中的同名文件
- run 结束时只更新 run 元数据中的完整度，不再做第二套“一次性总复制”

如果 run 是 `global`：

- 本轮不为 `global` run 生成 snapshot
- `global` run 完成后不再把用户默认导向新的 Results 主树
- `global` run 的结果仍留在现有课程产物与兼容 artifacts/export 路径中
- 若未来需要把 `global` 纳入新的结果工作台，再单独设计第二套展示区

## Route Semantics

### Run Routes

- `/runs`
  - 默认未开始运行工作台
- `/runs/[runId]`
  - 真实 run 工作台

### Results Routes

- `/courses/results`
  - 默认结果工作台
  - 若当前没有绑定 course，可展示“请选择课程”式的工作台内提示，但不再跳去单独空态页
- `/courses/[courseId]/results`
  - 指向当前课程结果工作台
  - 若带 `runId`，只作为当前 run 标识，不改变课程级主体结构

## Frozen UI Semantics

以下已有语义在本轮继续保留：

- preview 只用于内部调试
- 结果页自动刷新时保留展开和选中状态
- 导出过滤仍保留既有合同
- 配置页和输入页的产品简化决策保持不变
- `global` run 的现有 artifacts/export 兼容路径继续保留

以下已有语义被本轮显式替换：

- `/runs` 产品空态页
- `/courses/results` 产品空态页
- 结果页 `course-level latest run + scoped run 仅标签 + public artifact tree` 的主树合同

## Risks

- 这轮需要同时改 backend 持久化、read model、前端页面结构，不再是纯前端工作
- 如果不设计清楚 snapshot 生成时机，run 失败/清理后可能出现不一致快照
- 从旧 artifact tree 迁移到 snapshot tree 后，结果页和导出区的部分实现会需要重新接线

## Recommended Implementation Shape

建议拆三批：

1. backend snapshot contract + results snapshot read API
2. Run / Results 页面语义改造，去掉空态页
3. 文档、导出/预览接线与验证收口

这样可以先把数据合同打稳，再去改页面，而不是前端先猜存储结构。
