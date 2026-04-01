# Stitch V2 High-Fidelity Alignment Design

> Status: proposed  
> Owner: Codex  
> Date: 2026-04-01

## Summary

在前一轮 Stitch V2 迁移已经把默认产品路由切到 V2 workbench 的基础上，本轮继续推进“高保真对齐”。目标不是再做一次局部美化，而是把当前 GUI 的壳层、布局、配色、字体、图标、圆角、间距、卡片层级和按钮语义尽量对齐到 Stitch 导出的页面代码与视觉标尺，同时保留当前 GUI 已接上的真实功能和后端接口语义。

本轮遵循一个明确优先级：

1. 现有 GUI 已接上的真实功能必须继续可用
2. Stitch 的视觉系统与布局关系优先级高于当前 V2 的折中样式
3. Stitch 中多出来的组件优先映射成真实功能
4. 无真实功能但有产品信息架构价值的组件可改成“即将到来”
5. 与当前系统无关的组件才删除

## Why Now

当前 V2 迁移已经完成默认路由切换，但仍然是“以 Stitch 为参考”的实现，不是“以 Stitch 为母版”的实现。主要差距在：

- 字体系统仍以 `Geist` 为主，而不是 Stitch 的 `Manrope + Inter`
- 壳层、卡片、hero、侧栏和主画布的比例关系仍然偏向现有工程实现，而不是 Stitch 导出代码
- 圆角、边距、按钮、标签、深浅表面层次与 Stitch 仍有明显偏差
- 顶栏/左栏/次级动作还没有系统性处理多出来的 Stitch 组件

如果继续在当前 V2 上增量补样式，最终会长期停留在“像，但不够像”的状态。需要单独一轮设计和实施，把当前 V2 提升到接近 Stitch 代码母版的保真度。

## Goals

- 让默认产品页的视觉和布局尽量接近 Stitch 导出页面
- 把当前 GUI 已用接口全部接到高保真页面里，不丢功能
- 统一字体、图标、颜色 token、圆角、阴影、边距和层级体系
- 让 Stitch 多出来的组件按统一规则处理，而不是逐页临时决定
- 保持 preview 只作为内部调试入口，不进入产品默认路径

## Non-Goals

- 不改 backend API 合同
- 不重做 runtime 状态语义
- 不恢复已经在产品层隐藏的旧能力，例如课程链接输入、课程级 runtime override UI
- 不为了贴合 Stitch 强行引入无意义假功能
- 不要求和 Stitch HTML 逐字符一致；要求的是视觉系统、布局骨架和组件层级尽量一致

## Frozen Functional Contracts

以下合同在本轮保持冻结，视觉对齐不得破坏：

- 输入页继续只支持本地素材与手工字幕资产，不恢复课程链接 UI
- 配置页继续隐藏课程级 runtime override UI
- `AI 服务配置` 继续默认折叠
- 运行页继续使用真实 `RunSession`、SSE、日志、`resume/clean` 合同
- 结果页继续使用课程级 latest-run 状态、scoped run 仅标签、过滤导出、稳定文件树刷新
- `/runs` 与 `/courses/results` 继续是产品空态页
- `mode=preview` 继续是内部调试入口，不进入产品默认流

## Reference Assets

本轮高保真对齐必须逐页参考以下 Stitch 导出资源，而不是凭印象实现：

- `out/stitch/14050487305097227160/overview-v2-72223e80f4fc44f496faa80b5192e38f.html`
- `out/stitch/14050487305097227160/overview-v2-72223e80f4fc44f496faa80b5192e38f.png`
- `out/stitch/14050487305097227160/input-step1-v2-98412b91e37f42b78f70404496d85538.html`
- `out/stitch/14050487305097227160/input-step1-v2-98412b91e37f42b78f70404496d85538.png`
- `out/stitch/14050487305097227160/config-step2-v2-925e1adc724a4e948f7aff858c71d329.html`
- `out/stitch/14050487305097227160/config-step2-v2-925e1adc724a4e948f7aff858c71d329.png`
- `out/stitch/14050487305097227160/run-step3-v2-2732c03d32c84715a16587ceed205b9b.html`
- `out/stitch/14050487305097227160/run-step3-v2-2732c03d32c84715a16587ceed205b9b.png`
- `out/stitch/14050487305097227160/results-step4-v2-4d882ed4de034a6aa99c5bfe1123da05.html`
- `out/stitch/14050487305097227160/results-step4-v2-4d882ed4de034a6aa99c5bfe1123da05.png`

## Design Direction

### Typography

- 主要标题、hero、大号数字编号改成 `Manrope`
- 正文、标签、表单说明、次级文字改成 `Inter`
- 保留代码/monospace 只用于技术性内容，不再让主视觉混用 `Geist Mono`
- 标题字重、行高、字距尽量对齐 Stitch 导出代码

### Iconography

- 全站 UI 图标统一改用 `Material Symbols`
- 仅在品牌 Logo、文件类型图标或现有功能明确依赖自定义图形时保留例外

### Color System

- 使用 Stitch 导出里的核心 token 作为产品默认视觉系统
- 重点对齐：
  - `background`
  - `surface-container / low / high / highest`
  - `primary / primary-container / primary-fixed`
  - `outline / outline-variant`
  - `inverse-surface / inverse-on-surface`
- 当前 V2 中偏工程化的深色/浅色混搭、过于饱和的强调色、以及阴影强度不一致问题都要统一收口

### Radius / Spacing / Shadow

- 圆角向 Stitch 的小圆角体系收敛，不再默认使用过大的 28px/32px 容器圆角
- 页面间距、section padding、按钮高度、输入框内边距按 Stitch 标尺统一
- 阴影改成更轻、更贴近表面层级，而不是当前偏重的“悬浮卡片”效果

## Shell Alignment

当前 `AppShell` 已经有 Stitch V2 基础，但还不够像 Stitch。壳层需要进一步对齐：

- 顶栏结构更接近 Stitch 的 fixed top app bar
- 左侧导航更接近 Stitch 的 side rail 视觉关系
- 中间主画布与右侧上下文区的比例、留白、标题层级继续向 Stitch 收敛
- 顶栏状态和品牌区不再采用当前偏自定义的信息块样式，而是按 Stitch 的更轻壳层风格处理

## Extra Component Mapping Policy

### Rule Order

1. 能接真实功能就接真实功能
2. 没有真实功能但有信息架构价值就改成 `即将到来`
3. 与当前系统明确无关的再删除

### Shell-Level Mapping

| Stitch 组件 | 处理策略 |
| --- | --- |
| 顶栏主 CTA，例如 `Publish` | 优先映射到真实结果导出或完成态主动作；若当前页面不适合触发真实动作，则改成上下文感知 CTA，而不是保留假发布 |
| 顶栏次导航，如 `Curriculum / Assets / Settings` | 映射到当前四步产品导航及结果/资产语义，不复制 Stitch 的假栏目 |
| 侧栏工作区卡片 | 保留，映射到当前课程/草稿/运行上下文 |
| `New Chapter` | 可映射到输入页“新增手工章节资产”；若在非输入页无明确语义，则标记为 `即将到来` 或在页面内降级 |
| `Help / Archive` | 当前若无真实功能，可降级为 `即将到来` 或二级入口，不作为主操作 |

## Page-by-Page Alignment

### Overview

- 以 Stitch 的 bento/editorial 版式为准
- 现有四步产品流程继续存在，但视觉上要更接近 Stitch 的数字卡和主次卡关系
- 顶部状态、工作区概览、CTA 分组都往 Stitch 的结构靠
- 不再保留当前过度解释型文案和工程味过重的说明块

### Input

- 上传区、手工字幕资产区、摘要区、未来模态卡按照 Stitch Input 结构重组
- Stitch 中的视觉层级、分组标题、辅助卡片、上传区背景和边框语义尽量贴齐
- 继续保证：
  - 本地字幕上传
  - 手工章节资产编辑
  - 草稿摘要
  - 去配置页的真实导航
- 不恢复课程链接 UI

### Config

- 模板与生成策略卡成为页面主核
- `AI 服务配置` 继续保留折叠交互，但外观、展开面板和按钮样式按 Stitch 对齐
- 运行控制、模板摘要、全局构建入口按 Stitch 的主次层级重排
- 继续隐藏课程级 runtime override UI

### Run

- 页面更接近 Stitch 的监控工作台形态
- 把运行总状态、章节并发板、日志/数据通路面板的比例关系对齐 Stitch
- `resume/clean` 保持真实合同，但按钮层级、状态 badge、提示条要更接近 Stitch
- Preview 仍保留为内部调试入口，但视觉也要落在同一套设计系统里

### Results

- 文件树、预览、review/export 区域按 Stitch Results 的比例与表面层级对齐
- 结果头部、课程状态条、章节状态标签、导出控制都按 Stitch 视觉语言重做
- 保持以下语义不变：
  - 课程级 latest-run
  - scoped run 仅标签
  - 过滤导出
  - 自动刷新但不强制展开
  - 选中文件稳定

## Component Strategy

实现不应重新推翻上一轮 V2 结构，而应在 V2 结构上做高保真升级：

- 继续保留 `*-workbench-v2.tsx` 作为真实功能入口
- 新增或重写更贴近 Stitch 的 presentation sections / shared primitives
- 允许进一步细分：
  - header / rail / hero
  - stat card / action card / metric badge
  - page-specific framed sections
- 不把页面逻辑重新塞回一个巨型 workbench

## Expected File Direction

重点会继续集中在：

- `web/app/globals.css`
- `web/components/app-shell.tsx`
- `web/components/stitch-v2/*`
- `web/components/overview/*`
- `web/components/input/*-v2.tsx`
- `web/components/config/*-v2.tsx`
- `web/components/run/*-v2.tsx`
- `web/components/results/*-v2.tsx`

必要时允许新增更细的 Stitch 呈现组件，但不引入新的 UI 依赖库。

## Validation Requirements

### Static Validation

- 现有前端测试继续通过
- 新增测试覆盖：
  - 字体/图标/壳层对齐断言
  - 额外组件的语义映射断言
  - 关键页面仍保留真实功能入口

### Browser Validation

至少重新验证：

- `/`
- `/courses/new/input`
- `/courses/new/config`
- `/runs`
- `/courses/results`
- `/runs/preview?mode=preview&scenario=running`
- `/courses/preview/results?mode=preview&scenario=completed`

若 backend 准备就绪，再补真实 `Input -> Config -> Run -> Results` 流程。

## Risks

- 高保真对齐会碰到更多共享样式文件，单批次改动面明显大于上一轮 V2 迁移
- 改字体和图标可能导致局部尺寸、换行和卡片高度发生系统性变化，需要逐页复验
- 如果把 Stitch 多出来的组件接到真实功能上，必须避免误导用户；不能为了长得像而把语义做假

## Recommended Implementation Shape

建议把这轮实现拆成三个阶段：

1. 共享设计系统与壳层高保真对齐
2. 五页逐页高保真重排与额外组件映射
3. 文档、验证与视觉收口

这样可以避免一上来同时改完五页造成审查困难，也更适合后续继续用多子代理推进。
