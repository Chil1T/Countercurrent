# Databaseleaning GUI Web Product Design

**Goal:** 为 `databaseleaning` 建立一个本地优先、前后端分离、可继续部署的 Web 产品界面，用可视化流程替代纯 CLI 操作，并保持现有 pipeline/CLI/runtime contract 不被 GUI 侵入。

## Product Positioning

该 GUI 不是重写执行引擎，而是围绕既有 blueprint-first runtime 提供一个用户友好的产品壳层。

用户核心目标不是“看 AI 在思考”，而是：

1. 组织输入素材
2. 配置输出模板与参数
3. 理解阶段化运行状态
4. 检查结果文件与 reviewer 结论

## Product Shape

第一版采用四页主流程：

1. `输入页`
   - 输入课程链接
   - 上传字幕/课件/后续多模态素材
   - 输入教材名与可选 TOC
   - 识别并修正课程基础信息
2. `配置页`
   - 选择输出模板
   - 编辑模板参数
   - 查看该配置将产出什么
3. `运行页`
   - 显示运行状态
   - 显示阶段轨道与 resumable 状态
   - 预留数据通路可视化容器，但第一版不实现真正图谱
4. `结果页`
   - 文件树
   - 文件预览
   - reviewer 聚合信息
   - 导出 ZIP

## UX Principles

- 以流程感取代命令感，但避免做成一次性 wizard。
- 运行页强调阶段和可恢复性，不强调“AI 正在思考”。
- 配置页是第一版最重要的页面，它决定产物形态，必须比输入页更强。
- 结果页是高密度工作台，而不是单文件下载页。
- 多模态能力尚未完全实现，但输入页结构应先按多模态分区设计。

## Information Architecture

统一采用“流程壳 + 工作台”布局：

- 左侧：流程导航（输入 / 配置 / 运行 / 结果）
- 顶部：课程名、状态、最近运行时间、导出入口
- 中间：当前步骤的主工作区
- 右侧：课程摘要、模板摘要、运行摘要、review 摘要

### Input Page

- 左侧为素材输入分区
- 右侧为课程信息识别结果卡
- 分区包括：
  - 课程链接
  - 字幕
  - 音视频
  - 课件
  - 教材信息 / TOC
- 未支持能力以 “Coming soon” 形式占位，而不是等支持后再改结构

### Config Page

- 左：模板列表
- 中：模板参数编辑器
- 右：产物结构与影响摘要
- 参数组建议：
  - 输出模板
  - 内容密度
  - reviewer 策略
  - 章节范围
  - 命名与导出
  - 高级参数

### Run Page

- 顶部：运行总状态卡
- 中部：阶段轨道（blueprint / ingest / curriculum_anchor / gap_fill / compose_pack / review / canonicalize）
- 下部：阶段详情、错误摘要、resume 操作、日志抽屉
- 数据通路容器先稳定占位，未来再映射真实 runtime graph

### Result Page

- 左：文件树
- 中：文件预览（Markdown / JSON / text）
- 右：reviewer 聚合摘要、元数据、ZIP 导出

## Technical Direction

推荐路线：

- Frontend: `Next.js` + `TypeScript` + `Tailwind CSS` + `shadcn/ui`
- Backend: `FastAPI`
- State and forms: `TanStack Query` + `React Hook Form` + `Zod`
- Runtime updates: `SSE`

这条路线的核心不是 “双栈 + 调 CLI”，而是：

`Web Product` -> `Stable API` -> `Application/Orchestration Layer` -> `Execution Adapter` -> `Existing CLI/runtime`

## Backend Boundaries

### API Layer

- 输入校验
- 上传接口
- 课程草稿接口
- 运行创建/查询接口
- 结果读取接口
- SSE 事件接口

### Application Layer

- 创建课程草稿
- 更新输入素材
- 保存模板配置
- 启动运行
- resume / clean
- 聚合 reviewer 结果
- 导出 ZIP

### Adapter Layer

- `cli_runner`
- `runtime_reader`
- `artifact_exporter`
- `input_storage`

CLI 只允许存在于 adapter 层，前端和 API 不感知 CLI flags/subcommands。

## Core Domain Models

- `CourseDraft`
- `InputAsset`
- `TemplatePreset`
- `RunConfig`
- `RunSession`
- `StageStatus`
- `ArtifactNode`
- `ReviewSummary`

## Runtime Strategy

第一版采用：

- `LocalProcessRunner`
- 子进程调用现有 `processagent.cli`
- 轮询 `runtime_state.json`
- 映射为前端可消费的阶段事件
- 通过 `SSE` 推送给运行页

第二版可以替换为：

- `QueueRunner`
- Redis/Celery/RQ/Arq 等队列基础设施

因此第一版就必须抽象 `Runner` 接口，但不强制第一版引入队列。

## Frontend Component Strategy

`shadcn/ui` 负责：

- Card
- Form
- Input
- Tabs
- Accordion
- Sheet
- Dialog
- ScrollArea
- Resizable panels
- Dropdown / Popover / Tooltip

前端状态分层：

- 表单状态：`React Hook Form`
- 服务端状态：`TanStack Query`
- 运行流状态：`EventSource` + 页面级 hook
- 少量 UI 状态：局部 state 或轻量 `zustand`

## Debugging And QA

可直接利用的前端调试能力：

- `playwright-interactive`
- Playwright MCP browser tools

因此 Web 方案的功能调试与视觉 QA 已有现成工具链支持。

## MVP Scope

第一版 Done 标准：

1. 用户能创建课程草稿
2. 用户能配置输出模板
3. 用户能启动一次运行
4. 用户能看到阶段进度与错误
5. 用户能在结果页浏览文件树与预览
6. 用户能导出 ZIP

## Non-Goals For V1

- 多人协作
- 用户系统
- 真正的分布式 worker/queue infra
- 完整多模态处理能力
- 复杂数据通路可视化图谱

## Rollout

1. 搭建产品骨架
2. 输入页与课程草稿
3. 配置页与模板配置
4. 运行页最小闭环
5. 结果页最小闭环
6. 第二轮体验增强
