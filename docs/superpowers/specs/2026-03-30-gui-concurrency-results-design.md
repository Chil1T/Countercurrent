# GUI Concurrency And Results UX Design

**Goal:** 在保持当前 GUI 风格连续性的前提下，重构运行页与结果页的信息架构，使其正确表达多章节并发运行、课程级章节状态与按完成度导出的能力。

**Status:** approved for planning

## Context

2026-03-27 的 runtime/backend 一期已经完成：

- 非全局章节主流程支持多章节并发
- `RunSession` 已暴露 `chapter_progress[]`
- artifacts export 已支持 `completed_chapters_only=true`
- artifacts export 已支持 `final_outputs_only=true`

当前 GUI 的主要问题不再是接口缺失，而是前端仍按串行运行心智组织页面：

- 运行页仍以聚合 `stages[]` 为主轴，没有把章节并发状态作为一等信息
- 结果页文件树没有章节级状态标识
- 导出按钮仍只有默认 ZIP
- 文件树自动刷新时会把新增节点自动并入展开集合，破坏用户手动折叠状态
- 结果页左右布局虽然已分栏，但仍偏固定宽度，未针对深层树展开做更稳定的列策略

## Source Contracts

本次 GUI 设计基于以下既有合同，不新增 backend 需求作为前置条件：

- `RunSession.chapter_progress[]`
  - `chapter_id`
  - `status`
  - `current_step`
  - `completed_step_count`
  - `total_step_count`
  - `export_ready`
- `RunSession.stages[]`
  - 继续保留，作为课程级聚合数据通路摘要
- artifacts tree
  - 继续返回扁平 `nodes[] = { path, kind, size }`
- export URL filters
  - `completed_chapters_only=true`
  - `final_outputs_only=true`

## User Decisions

以下设计约束已确认：

- 功能优先，视觉语言保持当前风格即可，不追求单独的大改版
- 结果页的章节状态按课程级最新状态展示
- 如果结果页带 `runId` 进入，需要在文件树父层标识“当前 run”
- 运行页并发态采用章节卡片列表，不采用表格主视图
- 文件树自动刷新，但不得改变用户当前展开/折叠状态

## Approaches Considered

### Approach A: 保守接线

只在现有运行页上补一个章节列表，在结果页章节节点后补文本状态。

优点：

- 改动最小
- 风险最低

缺点：

- 运行页仍以串行 `stages[]` 叙事为主
- 并发状态容易继续显得“附属”

### Approach B: 双主视图

运行页以章节并发卡片作为主视图，课程级 `stages[]` 退为辅助轨道；结果页以“课程级状态文件树”承接章节状态、导出和预览。

优点：

- 最符合 runtime 新合同
- 信息层级最清晰
- 无需新增 backend 接口

缺点：

- 需要同时调整运行页和结果页两个主组件

### Approach C: 结果页中心化

运行页尽量轻量，结果页承担更多运行中状态和导出控制。

优点：

- 结果页能力集中

缺点：

- 用户在运行过程中需要跨页理解状态
- 与“运行页并发态清晰可读”的目标冲突

## Chosen Approach

选择 **Approach B: 双主视图**。

理由：

- 现有 backend 已同时提供课程级与章节级两层状态源
- 运行页最适合承载“当前执行态”
- 结果页最适合承载“文件 + 章节状态 + 导出”
- 可以在不改 backend 合同的前提下完成本轮目标

## Screen Design

### 1. 运行页

运行页改成“三段式信息结构”：

1. 顶部：运行总状态
2. 中部：章节执行面板
3. 底部或侧栏：课程级数据通路 / 错误与日志

#### 顶部：运行总状态

保留现有内容，但降低其视觉噪音：

- run headline
- run status badge
- Backend / Model / Base URL / Review / Target Output 摘要
- Resume / Clean 动作
- 跳转结果页入口

这一区域继续表达“本次 run 的全局身份”，但不承担并发章节进度的主要阅读任务。

#### 中部：章节执行面板

新增章节卡片列表，成为运行页第一主轴。

每个章节卡片展示：

- `chapter_id`
- 章节状态 badge：`pending / running / completed / failed`
- `current_step`
- 完成度：`completed_step_count / total_step_count`
- `export_ready`

视觉规则：

- `running` 章节用轻动画或高对比边框强调
- `completed` 章节可直接显示“可导出”
- `failed` 章节明确显示失败，不和课程级失败混淆

交互规则：

- 多章节允许同时处于 `running`
- 列表顺序以 blueprint/runtime 章节顺序为准，不按状态重排
- 运行中的章节不能因为后续刷新而跳位

#### 课程级数据通路

现有 `stages[]` 继续保留，但改名/降级为课程级摘要，不再是主要执行视图。

它回答的是：

- 这次 run 当前大致处在哪个课程级阶段
- 失败或运行中的聚合指针落在哪里

它不再承担逐章节进度表达。

### 2. 结果页

结果页改成“课程级状态文件树 + 预览 + 导出控制”。

#### 文件树父层

文件树父层展示：

- 课程级最新状态摘要
- 如果页面携带 `runId`，显示“当前 run”标识

这能同时区分：

- 课程当前的最新章节状态
- 用户这次进入页面所关联的具体 run

#### 章节节点

每个章节节点直接显示课程级状态标识：

- `completed`
- `running`
- `pending`
- `failed`
- `export_ready` 辅助标识

状态来源：

- 通过 `chapter_progress[]` 与 `chapters/<chapter_id>/...` 的树节点做 join
- 不从文件是否存在推断 completed

说明：

- 当前结果页按课程级最新状态展示，因此章节节点状态不绑定单次 `runId`
- `runId` 只作为页面上下文标识，不覆盖章节状态来源

#### 导出区

结果页导出区增加两个独立开关：

- 仅已完成章节
- 仅最终产物

它们映射到：

- `completed_chapters_only=true`
- `final_outputs_only=true`

组合规则：

- 两个开关同时开启时，导出两者交集

说明文案必须写清：

- “仅已完成章节”按严格 completed 口径
- “仅最终产物”只导出 `notebooklm/*`

## Refresh And Interaction Rules

### 文件树刷新

结果页继续自动刷新 artifacts，但遵守以下规则：

- 不重置 `expandedKeys`
- 不把新节点自动加入展开集合
- 不改变用户当前选中文件
- 仅在当前选中文件已不存在时，回退到第一个可预览文件

刷新后允许更新：

- 节点数量
- 章节状态 badge
- 导出可用性提示

### 文件树展开/折叠

展开状态成为纯前端用户状态，不再由“新树全量 key 合并”驱动。

推荐策略：

- 初始化首次载入时，按默认展开策略生成一次初始集合
- 后续刷新只做“保留现有 key + 丢弃已不存在 key”
- 新出现的文件夹默认折叠，除非它是当前选中文件的祖先路径

### 布局稳定性

结果页继续保持左右分栏，但调整为更稳定的列策略：

- 左列文件树保持独立列
- 右列预览列允许在必要时被压缩
- 左列宽度采用更弹性的 `minmax` 或可拖拽列宽策略，而不是过窄固定区间
- 深层树展开时，优先横向截断/滚动控制，不允许树块下沉到预览列下方

## Data Mapping

### 运行页

- run summary：`RunSession`
- chapter cards：`RunSession.chapter_progress[]`
- data pipeline summary：`RunSession.stages[]`

### 结果页

- tree nodes：artifacts tree
- chapter badges：`chapter_progress[]` 与 chapter folder join
- export toggles：`buildExportUrl(courseId, options)`

## Non-Goals

本轮不包含：

- 新增 backend 状态接口
- 改造课程级最新状态的独立 API
- 大幅重做品牌/视觉语言
- 结果页 run 历史比较视图

## Implementation Impact

前端主改动预计集中在：

- `web/components/run/run-session-workbench.tsx`
- `web/components/results/results-workbench.tsx`
- `web/lib/results-view.ts`
- `web/lib/api/artifacts.ts`
- 相关前端测试

如果在实现中发现“课程级最新状态”仅靠当前结果页加载路径无法稳定获得，则允许补一个很小的后端读取接口，但这属于实现期例外，而不是当前设计前提。

## Validation Targets

实现完成后应至少验证：

- 运行页并发章节卡片可实时更新
- 多个章节同时 `running` 时，页面不再表现为串行轨道
- 结果页章节节点能正确显示课程级状态与 `export_ready`
- 自动刷新不会强制展开文件树
- 当前选中文件在刷新后仍保持
- 导出两个过滤开关可正确拼接 URL 并得到预期结果
