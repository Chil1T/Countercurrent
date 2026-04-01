# Workstream: GUI Product Contract

## Scope

本文件记录当前 GUI 产品层的正式合同，只描述：

- 页面目标
- 信息来源
- 状态与行为规则
- 页面之间的上下文传递

本文件不约束：

- 页面布局
- 视觉样式
- 组件拆分
- 具体实现方式

## Route Contract

当前产品默认路由包括：

- `/`
- `/courses/new/input`
- `/courses/new/config`
- `/runs`
- `/runs/{run_id}`
- `/courses/results`
- `/courses/{course_id}/results`

内部调试预览路由包括：

- `/runs/preview?mode=preview&scenario=running`
- `/runs/preview?mode=preview&scenario=completed`
- `/courses/preview/results?mode=preview&scenario=running`
- `/courses/preview/results?mode=preview&scenario=completed`

规则：

- 产品流程不得自动把用户带入 preview route
- preview 只用于内部 UI 调试
- 产品默认路由应当优先使用真实 API 与真实 runtime contract

## Shared Context Contract

GUI 页面之间当前共享以下上下文标识：

- `draftId`
- `courseId`
- `runId`

规则：

- 输入页与配置页至少应能保留 `draftId`
- 运行页与结果页在拥有真实 `runId` / `courseId` 时，应继续保留这些上下文
- 当用户从运行页或结果页返回输入/配置页时，不应无故丢失已有上下文
- 不允许发明 `demo`、`preview-run` 一类伪产品上下文来替代真实标识

## Input Page Contract

输入页的产品目标是建立一个可执行的课程草稿。

当前最小可执行输入是：

- `book_title`
- 至少一个可落盘的字幕/转录输入

当前产品规则：

- 产品界面只暴露本地素材输入
- “课程链接”入口当前已从产品界面隐藏
- 多字幕输入允许多个资产，但规范化后的文件名必须唯一
- 若两个上传项最终会写到同一个输入文件名，后端会拒绝创建草稿
- 当输入成功创建草稿后，页面必须获得并保留 `draftId` 与 `courseId`

输入页的事实源当前包括：

- `POST /course-drafts`
- `GET /course-drafts/{draft_id}`

## Config Page Contract

配置页的产品目标是为既有草稿补齐运行所需的模板与 AI 服务配置。

当前产品规则：

- “AI 服务配置”属于 GUI runtime config 的产品入口
- 课程级运行时覆盖编辑器当前从产品界面隐藏
- 历史草稿中若已存在课程级覆盖值，runtime 仍会继续解析
- “课程链接”不再是配置页主路径的一部分
- 配置页应支持保存模板配置，并基于当前草稿进入运行创建/继续逻辑

配置页的事实源当前包括：

- `GET /templates`
- `GET /gui-runtime-config`
- `PUT /gui-runtime-config`
- `POST /course-drafts/{draft_id}/config`
- `GET /course-drafts/{draft_id}`

## Run Page Contract

运行页的产品目标是表达当前课程运行的真实状态，并允许用户执行受约束的运维动作。

当前运行页存在两种合法形态：

1. 未开始工作台
2. 真实 run 工作台

未开始工作台规则：

- `/runs` 不再使用独立产品空态页
- 即使尚未创建真实 run，也应直接渲染工作台
- 未开始态必须明确标注“任务未开始”
- 未开始态下不得伪造真实运行进度
- `resume` / `clean` 在未开始态下必须禁用

真实 run 工作台规则：

- 事实源优先是 `GET /runs/{id}`
- 可通过 `GET /runs/{id}/events` 订阅运行状态变化
- 可通过 `GET /runs/{id}/log` 与 `GET /runs/{id}/log/events` 获取日志
- `resume` 只允许作用于当前 run
- `clean` 只允许作用于当前 run
- 页面状态不得仅凭前端本地推断，必须以 `RunSession` 与 runtime 文件为准

运行页当前必须正确表达：

- `backend`
- `hosted/heuristic`
- `simple_model`
- `complex_model`
- `review_mode`
- `target_output`
- `stages[]`
- `chapter_progress[]`
- `last_error`

## Results Page Contract

结果页的产品目标是展示当前课程可读的最终产物，并提供结果导出与 review 摘要读取。

当前结果页存在两种合法形态：

1. 默认结果工作台
2. preview 调试工作台

默认结果工作台规则：

- `/courses/results` 不再使用独立产品空态页
- 即使尚无当前课程快照，也应直接渲染结果工作台
- 结果页主树当前以 `results-snapshot` 为事实源
- 主树只展示最终目标 `.md`
- `intermediate/*.json`、`runtime/*`、`review_report.json` 不进入主树

结果页主树分区规则：

- `过去课程产物`
- `当前课程产物`

分区语义：

- 过去课程产物：其他 `course_id` 的历史 run 快照
- 当前课程产物：当前 `course_id` 下按 `run_id -> chapter_id -> notebooklm/*.md` 展示的最终产物

`runId` 规则：

- 当当前 URL 带 `runId` 时，可在当前课程分区内标注“当前 run”
- 该标识只是 scoped label
- 章节状态与加载提示仍应优先来自课程级最新状态，而不是 scoped run 自身

结果页当前必须正确表达：

- snapshot 树
- 文件内容预览
- review summary
- 导出过滤
- 课程级最新状态
- scoped run 标识

## Export Contract

GUI 当前支持两类导出过滤：

- `completed_chapters_only=true`
- `final_outputs_only=true`

产品规则：

- 默认导出不应自动打开任何过滤条件
- 仅当用户显式选择时，才附加过滤参数
- 结果页可以组合这两个过滤条件
- 过滤导出基于后端 artifacts/export 合同，不由前端自行推断章节是否完成

## State And Refresh Rules

当前 GUI 的正式状态规则包括：

- 运行状态优先来自 `RunSession`
- 章节完成态优先来自 `chapter_progress[].export_ready`
- 结果页章节状态优先来自课程级 `latest_run`
- 文件树刷新时必须尽量保留当前展开/折叠与选中状态
- `SSE` 断线可以显示警告，但不应直接把页面整体切成失败态
- 结果页若在 run 尚未完成时已打开，应允许随着 `run.update` 自动刷新结果视图

## Rewrite Baseline

如果后续彻底重写 GUI，新的实现至少应继续满足本文件和下列正式合同：

- [`docs/runbooks/gui-dev.md`](../runbooks/gui-dev.md)
- [`docs/runbooks/run-course.md`](../runbooks/run-course.md)
- [`docs/schemas/gui-api-models.md`](../schemas/gui-api-models.md)
- [`docs/workstreams/blueprint-runtime.md`](blueprint-runtime.md)
