# Stitch V2 Frontend Migration Design

**Goal:** 以 Stitch 项目 `ReCurr 结果 (Step 4)` 的五页视觉稿为目标界面，高保真重建 GUI 的页面骨架与视觉系统，同时完整保留当前 `databaseleaning` Web GUI 已有的真实功能、状态合同与调试能力。

**Status:** approved for planning

## Context

当前 GUI v1 已经具备真实产品闭环：

- 首页 / 输入 / 配置 / 运行 / 结果 五页主流程
- 本地字幕与多章节素材输入
- 模板保存与 AI 服务配置
- 真实 `LocalProcessRunner`
- `SSE` 运行状态、`resume` / `clean`
- 并发章节卡片、课程级结果状态
- 结果树、预览、review 摘要与过滤导出
- 内部 `preview` 模式与产品空态页

但页面视觉成熟度与 Stitch 外部设计稿仍有明显差距：

- 页面骨架、层次、版式叙事、卡片层级仍偏工程态
- 首页与空态页的产品表达力不足
- `Input / Config / Run / Results` 四页的设计语言虽已统一，但与 Stitch 成熟稿相比仍显保守
- 现有 `workbench` 组件承担了过多“功能 + 视觉骨架”职责，不利于做高保真迁移

用户已经确认本轮目标更偏向 Stitch 高保真落地，而不是只借鉴风格。

## Source Inputs

本次迁移以以下外部设计产物为视觉母版：

- 项目：`ReCurr 结果 (Step 4)`
- Project ID: `14050487305097227160`
- Screens:
  - `ReCurr 概览 (Overview) - V2`
  - `ReCurr 输入 (Step 1) - V2`
  - `ReCurr 配置 (Step 2) - V2`
  - `ReCurr 运行 (Step 3) - V2`
  - `ReCurr 结果 (Step 4) - V2`

这些产物已下载到：

- `out/stitch/14050487305097227160/`

其中每个 screen 都包含：

- `screenshot`
- `htmlCode`

说明：

- Stitch 的 screenshot / html 只作为视觉与骨架参考
- 不是前端生产代码的直接来源
- 最终页面必须继续遵循现有 Next.js / React / Tailwind / App Router 结构

## User Decisions

本轮设计约束已确认：

- 目标偏向 Stitch 高保真覆盖，而不是低保真吸收
- 优先覆盖当前产品默认页面，而不是只做调试版样式
- `preview` 继续保留为内部调试能力，不进入正常产品导航
- 正常从输入页 / 配置页进入运行或结果页时，应进入产品空态或真实页，不进入 preview
- 当前 GUI 中已经上线的真实功能，一个都不能丢

## Non-Goals

本轮不包含以下内容：

- 不重做 backend API、runtime contract、CLI contract
- 不因贴合 Stitch 而更改 `RunSession`、`CourseResultsContext`、artifacts export 等核心语义
- 不把 Stitch HTML 原样嵌入到生产代码
- 不新增大型 UI 框架或状态管理依赖
- 不把内部 preview 模式变成面向用户的产品功能

## Frozen Contracts

以下合同在本轮迁移中允许复用和重新封装，但**不允许改义**：

### Runtime / API Contracts

- `CourseDraft` 创建、读取、配置保存合同
- `RunSession` 的状态、`stages[]`、`chapter_progress[]`、`last_error`
- `CourseResultsContext.latest_run`
- artifacts tree / content / review summary / export filters
- `resume` / `clean` / `run.log` / `run.update` 的现有 API 语义

### UI Semantics Contracts

- 运行页：
  - `Resume` / `Clean` 的禁用与可用条件
  - `SSE` 驱动的运行状态更新
  - 日志预览与日志流的现有增量行为
- 结果页：
  - 章节状态按课程级最新状态展示
  - `runId` 只作为 scoped view 标识，不覆盖课程级状态来源
  - `completed_chapters_only` 与 `final_outputs_only` 语义保持不变
  - 文件树自动刷新时保留用户展开/折叠与当前选中状态
- preview：
  - 只在显式 `mode=preview` 下启用
  - 不进入默认产品导航
- 空态：
  - 正常产品流进入 `/runs` 与 `/courses/results` 时显示产品空态，而不是 preview

### Bridge Layer Allowed Scope

Feature bridge 唯一允许做的适配是：

- 调整组件边界
- 重新组织数据映射
- 重排信息层级
- 把现有功能挂到新骨架

Feature bridge 不允许：

- 修改 API 返回结构
- 改变 loader/action 语义
- 重定义 preview 边界
- 修改导出过滤、课程级状态、`resume` / `clean` 等既有产品语义

## Problems To Solve

1. 需要把 Stitch 的视觉质量迁移到产品默认路由，而不是停留在参考稿。
2. 需要避免“外观像 Stitch，但行为退化”。
3. 需要在迁移过程中控制回归风险，不能让 `run / results` 这种高状态密度页面被一次性重写后失稳。
4. 需要给执行 agent 一个长期可落地的分阶段计划，而不是“一次性大改”。

## Approaches Considered

### Approach A: 渐进换肤

只在现有页面上替换样式和局部布局，尽量不改组件边界。

优点：

- 风险最低
- 最容易保留现有行为

缺点：

- 很难高保真接近 Stitch
- 现有 `workbench` 的骨架限制太强，最终只能“像一点”

### Approach B: 全量双轨迁移

新建完整 `Stitch V2` 页面骨架、共用展示组件与中间桥接层，逐页把真实功能挂回去；旧页面暂时保留，待 V2 完成后切主路由并清理旧实现。

优点：

- 最容易达到高保真
- 可以分阶段回归，不必一次性赌全量原地重构
- 视觉层与功能层边界更清晰

缺点：

- 迁移期间会有短期双轨代码
- 计划与验收复杂度更高

### Approach C: 原地重构

直接在现有页面和 `workbench` 里大改骨架，尽量不增加新文件。

优点：

- 短期文件数量少

缺点：

- 风险最高
- 容易把现有功能、测试和视觉同时搅乱
- 不适合作为长时间自动执行目标

## Chosen Approach

选择 **Approach B: 全量双轨迁移**。

但这里的“双轨”是有限双轨，不是长期维护两套产品：

- 旧页面只作为迁移期 fallback
- 新页面承担最终默认路由
- 完成后旧页面应删除或退到内部历史分支，不长期保留

选择理由：

- 只有重新建立 Stitch V2 的页面骨架和展示组件，才能高保真接近外部设计稿
- 当前真实业务逻辑已经可用，不应该为视觉迁移而重写 backend-facing 功能
- `run / results` 页状态复杂度高，需要逐页迁移并保留强回归能力

## Design Principles

### 1. Stitch 决定视觉与骨架

Stitch 页面提供：

- 整体页面气质
- 顶栏 / 侧栏 / hero / 主副栏布局
- 卡片等级与色彩层次
- 重点模块的版式主次关系

### 2. 当前 GUI 决定真实行为

现有 Web GUI 继续提供：

- 真实草稿、配置、运行、结果、导出行为
- 真实状态源
- 真实路由语义
- 真实空态 / preview 边界

### 3. 功能完整性优先于像素级模仿

如果 Stitch 某个交互或按钮没有真实产品语义：

- 可以改写
- 可以降级为展示组件
- 不能直接冒充成可用主操作

### 4. 视觉层与功能层解耦

迁移后应让以下边界更清晰：

- Design tokens / shared presentation
- Page shell / layout composition
- Feature workbench / API wiring

## Target Architecture

### Layer 1: Stitch V2 Design System

职责：

- 统一颜色、字体、圆角、阴影、按钮、表单、badge、panel 样式
- 统一卡片层级与深浅面板关系
- 把 Stitch 的设计语言沉淀为共享 token 和基础组件

建议落点：

- `web/app/globals.css`
- `web/components/app-shell.tsx`
- 新增共享 presentation components / style helpers

### Layer 2: Stitch V2 Page Shell

职责：

- 顶栏、侧栏、页面 hero、上下文摘要、主副列布局
- Overview / Step 1 / Step 2 / Step 3 / Step 4 的统一页面骨架
- 产品空态骨架

说明：

- 这一层负责“长得像 Stitch”
- 但不直接承担数据获取和状态机逻辑

### Layer 3: Feature Bridges

职责：

- 把现有真实功能挂进新骨架
- 例如：
  - Input bridge 接 `createCourseDraft`
  - Config bridge 接 `saveCourseDraftConfig` / `saveGuiRuntimeConfig`
  - Run bridge 接 `getRun` / `resumeRun` / `cleanRun` / SSE / logs
  - Results bridge 接 `artifacts` / `results-context`

说明：

- 尽量复用已有数据流和状态模型
- 避免在视觉迁移阶段重写成熟业务逻辑

## Page-By-Page Target State

### Overview

目标：

- 采用 Stitch Overview 的 editorial hero 与强叙事入口
- 但页面导航仍然是当前真实四步流程

必须保留：

- 真实四步入口
- 产品空态与真实路由的区别

### Input

目标：

- 高保真吸收 Stitch Input 的主上传区、coming-soon 卡、信息组织方式

必须保留：

- 本地字幕文件上传
- 多章节手工字幕资产输入
- 草稿创建
- 草稿识别摘要
- 当前“只支持本地素材，不再暴露课程链接”的产品约束

### Config

目标：

- 高保真吸收 Stitch Config 的主配置区和辅助摘要区
- 突出模板与 AI 服务配置的主次关系

必须保留：

- 模板选择
- review 设置
- `AI 服务配置`
- 保存模板配置
- 启动 / 继续运行
- 更新全局汇总

必须继续遵守：

- `AI 服务配置` 默认折叠
- 课程级运行时覆盖 UI 暂时隐藏

### Run

目标：

- 高保真吸收 Stitch Run 的状态总览与监控工作台感

必须保留：

- 运行总状态
- 并发章节卡片
- 课程级数据通路
- 日志面板
- `Resume` / `Clean`
- 结果页跳转
- preview 调试态

必须继续遵守：

- 产品流空态页与 preview 调试态分离
- `runId` 不存在时进入 `/runs` 空态，而不是 preview

### Results

目标：

- 高保真吸收 Stitch Results 的成品工作台感

必须保留：

- 课程级状态文件树
- 运行中自动刷新
- 章节状态 badge
- 文件预览
- review 摘要
- ZIP 导出与过滤导出
- scoped run label
- preview 调试态

必须继续遵守：

- 章节状态按课程级最新状态展示
- `runId` 只作 scoped view 标识
- 产品流空态页与 preview 调试态分离

## Feature Parity Contract

计划执行结束后，以下矩阵必须全部满足。这份矩阵同时是第 7 阶段“默认路由切换”的 release gate。

| 页面 / 领域 | 必须保留 | 必须继续遵守 |
| --- | --- | --- |
| Overview | 真实四步入口、首页主入口说明 | 不引入假主操作替代真实流程入口 |
| Input | 创建草稿、读取草稿、上传字幕文件、多字幕资产手工输入、跳转配置页、草稿摘要 | 继续只支持本地素材，不恢复课程链接产品入口 |
| Config | 模板选择、内容密度、review 设置、AI 服务配置保存、保存模板配置、启动 / 继续运行、更新全局汇总 | `AI 服务配置` 默认折叠；课程级运行时覆盖 UI 继续隐藏 |
| Run | 获取 run、`SSE` 更新、日志预览与日志流、`resume`、`clean`、运行总状态、并发章节卡片、课程级数据通路、结果页跳转、运行空态 | `Resume` / `Clean` 语义不变；preview 与产品空态分离；无 `runId` 时进入 `/runs` 空态 |
| Results | artifacts tree、artifact preview、review summary、`completed_chapters_only`、`final_outputs_only`、运行中自动刷新、产品空态、scoped run label | 章节状态按课程级最新状态展示；`runId` 仅作 scoped view 标识；文件树刷新不打断用户当前展开与选中 |
| Debug / Internal | preview 路由仍可用 | preview 不进入默认导航，且只在显式 `mode=preview` 下可达 |

## Route Strategy

迁移后路由分成三类：

### 1. 默认产品路由

- `/`
- `/courses/new/input`
- `/courses/new/config`
- `/runs`
- `/runs/[runId]`
- `/courses/results`
- `/courses/[courseId]/results`

这些路由最终都应使用 Stitch V2 的页面骨架。

#### Route Contract Table

| Route | 权威语义 | 数据范围 | 空态触发条件 | 默认进入来源 / 行为 | Preview 边界 |
| --- | --- | --- | --- | --- | --- |
| `/runs` | 产品运行空态页 | 无具体 run；可携带 `draftId` / `courseId` 作为上下文 | 没有真实 `runId` 时 | 从输入页 / 配置页点击“运行”且当前还没有真实 run | 不启用 preview；仅空态 |
| `/runs/[runId]` | 真实运行页 | 单个 `RunSession` + 日志 + SSE | 无 | 配置页成功启动 / 继续运行后进入；或从结果页 / 导航回到既有 run | 仅当显式 `mode=preview` 时使用 preview 数据 |
| `/courses/results` | 产品结果空态页 | 无具体课程结果；可携带 `draftId` / `courseId` 作为上下文 | 没有可展示的真实课程结果上下文时 | 从输入页 / 配置页点击“结果”且还没有真实课程结果 | 不启用 preview；仅空态 |
| `/courses/[courseId]/results` | 真实结果页 | 单课程 artifacts、review、course results context；可选 scoped `runId` | 无 | 从运行完成页、导航、结果页刷新进入 | 仅当显式 `mode=preview` 时使用 preview 数据 |

#### Detailed Rules

- `/runs`
  - 是产品空态路由，不是 404，不是 preview
  - 可显示“尚未创建运行”提示，并保留 `draftId` / `courseId` 上下文
- `/runs/[runId]`
  - 是唯一的真实运行详情路由
  - 如果 URL 含 `mode=preview`，则只把该页面作为内部调试页
- `/courses/results`
  - 是产品结果空态路由，不是 404，不是 preview
  - 可显示“尚无运行结果”提示，并保留 `draftId` / `courseId` 上下文
- `/courses/[courseId]/results`
  - 是唯一的真实课程结果详情路由
  - 如果携带 `runId`，只作为 scoped label 使用
  - latest / scoped 的归属保持现有语义：章节状态跟随课程级 `latest_run`，不是 `runId`
- 从 Config 页进入这些路由的精确行为：
  - 若尚未创建 run，点“运行”进入 `/runs`
  - 若尚未产生课程结果，点“结果”进入 `/courses/results`
  - 若已创建并持有真实 `runId` / `courseId`，导航进入对应真实详情路由
- preview 查询参数边界：
  - 只有显式 `mode=preview` 才启用 preview
  - `scenario` 只在 preview 下生效
  - `runId=preview-run`、`courseId=preview` 之类伪上下文不应再成为产品流入口判断条件

### 2. 内部调试路由

仍使用现有 preview 约定：

- `/runs/preview?mode=preview&scenario=...`
- `/courses/preview/results?mode=preview&scenario=...`

这些路由只服务内部 UI 调试。

### 3. 迁移期 fallback

在迁移中允许短暂保留旧版实现入口，但：

- 不应暴露给默认产品流
- 不应长期存在

## Migration Sequence

本设计要求计划按以下大阶段执行：

1. 共享设计系统与壳层基础
2. Overview 与空态
3. Input V2
4. Config V2
5. Run V2
6. Results V2
7. 默认路由切换
8. 旧实现退场、文档与验证收口

详细步骤由 implementation plan 展开。

### Phase Gates

每个大阶段都必须定义 entry / exit criteria。最低门槛如下：

1. 共享设计系统与壳层基础
   - Exit:
     - 共享 token / shell 已建立
     - 首页与现有页面可共存，不破坏当前导航
2. Overview 与空态
   - Exit:
     - `/`、`/runs`、`/courses/results` 已切到 Stitch V2 风格
     - 产品空态与 preview 调试态边界已通过测试锁定
3. Input V2
   - Exit:
     - 创建草稿、上传素材、跳转配置页完整可用
4. Config V2
   - Exit:
     - 保存模板配置、保存 AI 服务配置、启动 / 继续运行、更新全局汇总可用
5. Run V2
   - Exit:
     - 运行总状态、并发章节、日志、`resume` / `clean`、结果跳转全部可用
6. Results V2
   - Exit:
     - 文件树、预览、课程级章节状态、review 摘要、过滤导出全部可用
7. 默认路由切换
   - Exit:
     - 默认产品路由全部指向 V2
     - 通过 release gate 验证清单
8. 旧实现退场、文档与验证收口
   - Exit:
     - 旧实现已删除或脱离默认流
     - 文档、测试与 runbook 已同步

### Release Gate For Route Cutover

第 7 阶段切换默认路由前，至少必须通过：

- 一条完整产品主流程 smoke：
  - `Input -> Config -> Run -> Results`
- 一条运行控制流程 smoke：
  - `Run -> resume / clean -> 状态恢复`
- 一条结果页回归 smoke：
  - 文件树、章节状态、导出过滤
- 一条内部 preview smoke：
  - 显式 `mode=preview` 下的运行页与结果页仍可打开
- `Feature Parity Contract` 全项通过

## Risks

### 1. 视觉迁移掩盖功能回归

风险：

- 页面看起来更好，但真实 API 接线丢失或语义退化

应对：

- 每页建立功能等价验收清单
- 每批都跑最小可执行验证

### 2. 双轨期间组件重复

风险：

- 临时双轨导致局部逻辑重复、测试重复

应对：

- 明确迁移完成后删除旧骨架
- 桥接层复用现有工作流逻辑，而不是复制 API 逻辑

### 3. `run / results` 页状态复杂，最容易失真

风险：

- 并发章节、课程级状态、自动刷新、过滤导出可能在重排后失效

应对：

- 把 `Run V2` 与 `Results V2` 设为独立重批
- 明确这些页面的关键语义不可改动

### 4. 外部设计稿与真实产品语义不一致

风险：

- Stitch 里的某些假操作诱导实现偏离真实产品

应对：

- 明确“Stitch 决定外观，现有 GUI 决定行为”
- 对无真实语义的 UI 做本地化重写

## Testing Strategy

实施计划必须至少覆盖以下验证层：

### Frontend Unit / Source Tests

- shell/nav route tests
- preview boundary tests
- input/config/run/results 页面关键结构测试
- 导出、文件树、章节状态、空态、preview 相关测试

### Frontend Static Checks

- `npm run lint`
- `npm run build`

### Browser QA

至少人工核查：

- 首页
- 输入页
- 配置页
- 运行空态 / 真实运行页
- 结果空态 / 真实结果页
- preview 路由

### Regression Focus

重点回归：

- 输入页创建草稿
- 配置页启动运行
- 运行页并发章节卡片与日志
- 结果页文件树 / 状态 / 导出
- 空态页与 preview 分界

### Required Smoke Flows

implementation plan 至少要把以下 smoke flow 写成显式验证任务：

1. 主流程 smoke
   - 输入页创建草稿
   - 配置页保存模板
   - 启动真实运行
   - 进入真实结果页
2. 运行控制 smoke
   - 打开真实运行页
   - 执行 `resume` 或 `clean`
   - 验证状态与日志行为未退化
3. 结果页语义 smoke
   - 验证课程级最新状态
   - 验证 scoped run label
   - 验证过滤导出
4. 内部调试 smoke
   - 显式 `mode=preview` 的运行页与结果页均可打开

## Documentation Impact

计划执行结束后，至少需要同步：

- `docs/runbooks/gui-dev.md`
- 如页面行为或导航语义变化较大，补充 `docs/README.md`
- 若协作规则发生变化，再评估是否需要更新 `AGENTS.md`

## Success Criteria

本次迁移完成的标准是：

1. 产品默认页面已切到 Stitch V2 骨架。
2. 当前 GUI 已有真实功能全部可用，没有功能退化。
3. preview 仍保留为内部调试能力，但不进入产品默认流。
4. 运行空态、结果空态、真实运行页、真实结果页边界清晰。
5. `npm run lint`、`npm run build`、关键前端测试通过。
6. 文档已反映新的前端结构与调试边界。
