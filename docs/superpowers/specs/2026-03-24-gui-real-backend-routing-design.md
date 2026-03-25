# Databaseleaning GUI Real Backend Routing Design

**Goal:** 在现有 GUI v1 的真实运行链基础上，接入 hosted LLM backend 配置与两层模型路由，使 GUI 可以真正驱动 `openai`、`openai_compatible`、`anthropic` 等后端，而不是固定落到 `heuristic`。

## Problem Statement

当前 GUI 已经具备真实 `run-course` / `resume-course` / `clean-course` 调用能力，但 hosted backend 仍未接通：

- 配置页只保存模板、`content_density`、`review_mode`、`export_package`
- `RunService.create_run()` 仍然硬编码 `backend = heuristic`
- `CourseRunSpec` 只承载 `backend`、`review_mode`、`target_output`
- GUI 里没有 provider / API key / base URL / model 的产品配置层

结果是：

- 运行页会很快 `completed`
- 结果页只能看到 heuristic 级别的轻量差异
- 用户无法从 GUI 验证 hosted backend 的真实生成行为

同时，`clean` 的状态语义仍然容易误导：清理完成后不应显示“正在执行”，而应明确标成“已清理，待下一次运行”。

## Product Decision

真实后端接线采用：

- `全局默认值 + 课程级覆盖`
- `simple_model + complex_model` 两层模型路由
- 敏感配置允许在 GUI 内录入，并以明文形式保存到仓库外的本地配置文件

第一版只解决“真实配置进入 runtime contract”与“运行页状态可信”两个问题；不额外引入系统凭据管理器、多人配置同步或复杂的 per-stage 可视化编排器。

## Configuration Model

### Local GUI Config

新增 GUI 本地配置文件，存放在仓库外的用户目录中：

- Windows path: `C:\Users\<user>\.codex\databaseleaning\gui-config.json`

该文件保存：

- 默认 provider
- provider 对应的 API key
- provider 对应的 base URL
- 默认 `simple_model`
- 默认 `complex_model`
- 默认 timeout（可选）

这是 GUI 级默认值，不是课程配置本身。

API key 的传播边界必须明确：

- 仅保存在 GUI 本地配置文件中
- 仅在具体 `run-course` / `resume-course` 子进程启动时注入对应 provider 的环境变量
- 不允许通过修改 FastAPI 服务进程的全局环境来保存或传播 key

### Course-Level Runtime Config

课程级配置在现有 `DraftConfig` 上扩展，保存：

- `provider`
- `base_url`
- `simple_model`
- `complex_model`
- `use_global_credentials` / 或直接以“空值表示继承全局”

课程级配置负责表达“这门课本次希望怎么跑”，全局配置负责提供默认值和密钥。

### Resolution Rule

运行时按以下顺序解析：

1. 课程级显式值
2. GUI 全局默认值
3. CLI / provider 内建默认值

如果最终 provider 为 hosted backend，但缺少必需 API key，则在 GUI 层和 API 层直接报错，不启动 run。

如果 `base_url` 非法、规范化失败，或 `timeout_seconds <= 0`，也必须在 GUI/API 层直接报错，不创建 run。

## Runtime Routing Model

GUI 不开放所有 stage 的独立模型配置，第一版只提供：

- `simple_model`
- `complex_model`

映射规则：

- `blueprint_builder` -> `simple_model`
- `curriculum_anchor` -> `simple_model`
- `canonicalize` -> `simple_model`
- `gap_fill` -> `complex_model`
- `compose_pack` -> `complex_model`
- `review` -> `complex_model`

这条规则需要由 GUI 编排层转换成 CLI 的 stage-specific flags，而不是要求前端理解 CLI 参数面。

## Backend Integration Boundary

### GUI Config Service

在 `server` 中新增 GUI 配置服务，职责：

- 读取/写入本地 `gui-config.json`
- 解析默认 provider/base URL/model
- 生成 provider 级运行配置

该服务不直接启动 pipeline，只负责配置管理。

### Draft Config Extension

`CourseDraftService.save_config()` 从“模板配置保存”升级为“模板配置 + runtime backend 配置保存”。

扩展后的 `DraftConfig` 仍然是产品模型，不直接暴露 CLI flags，但要包含足够信息让 `RunService` 解析出：

- `backend`
- `base_url`
- `model`
- `blueprint_builder_model`
- `curriculum_anchor_model`
- `gap_fill_model`
- `compose_pack_model`
- `review_model`
- `canonicalize_model`
- `review_mode`
- `target_output`

### RunService

`RunService` 负责把 `DraftConfig + GUI config defaults` 翻译成真实运行参数。

它不应该把 provider 解析逻辑放进前端，也不应该要求 `LocalProcessRunner` 知道课程级继承规则。

`RunService` 需要做到：

- `create_run` 解析真实 backend config
- `resume_run` 继续使用该 run 创建时已冻结的 backend/base_url/model routing 摘要
- `clean_run` 不要求 provider，也不进入 running 语义
- `RunSession` 持久化当前 run 使用的 backend/base_url/model routing 摘要

`resume` 的规则明确为：

- `resume` 是继续同一个 run / checkpoint
- 如果用户修改了 provider/model，希望切换运行配置，应创建新的 run，而不是复用旧 `run_id`

### LocalProcessRunner

`LocalProcessRunner` 仍然只负责参数拼装和 subprocess 执行。

新增支持：

- `--backend`
- `--base-url`
- `--model`
- 各 stage model flags
- 可选 timeout
- provider 对应 API key 的 per-run 环境变量注入

`clean-course` 仍然不应接收 hosted backend 参数。

## Run Status Semantics

### Clean

`clean` 的语义是“删除当前课程 runtime artifacts”，不是“启动一次后台执行任务”。

因此：

- 点击 `Clean` 后，`RunSession.status` 应进入 `cleaned`
- 阶段轨道应重置为 `pending`
- 顶部摘要应显示“已清理，等待下一次启动/继续运行”
- 只有真正执行 `run-course` 或 `resume-course` 时才进入 `running`

### Fast Hosted/Heuristic Runs

无论运行多快，运行页都必须清楚显示：

- 当前 provider/backend
- 当前 `simple_model`
- 当前 `complex_model`
- 当前 `review_mode`
- 当前 `target_output`
- 本次是否为 hosted backend

这样即使 run 很快完成，用户也能判断“是否真的走了远程模型”。

## Frontend Changes

配置页新增两组配置：

### GUI Default Settings

- provider
- API key
- base URL
- simple model
- complex model

这部分可单独放在“运行后端设置”区块中，提供保存到本地配置文件的动作。

### Course Runtime Overrides

在现有模板配置旁边增加：

- backend/provider 选择
- base URL 覆盖
- simple model 覆盖
- complex model 覆盖

若字段留空，则显示“继承全局默认值”。

运行页摘要新增：

- provider/backend
- hosted / heuristic 标识
- simple/complex model summary
- clean 后的明确状态说明

## Validation Strategy

后端需要新增或扩展测试，覆盖：

- GUI config 读写
- `DraftConfig` 保存与回读 provider/model 覆盖
- `create_run` 将 GUI 配置映射成 runner spec
- `resume_run` 冻结并复用原 run 的 routing 规则
- `clean_run` 不进入 running，也不附带 hosted backend flags
- hosted API key 通过 per-run env 注入，而不是进程级全局环境
- 缺 key / 非法 `base_url` / 非法 timeout 时，run 在 API 层直接拒绝创建
- 服务重启后，`RunSession` 仍保留 hosted 摘要与 `cleaned` 语义

前端至少需要：

- 配置页默认值与课程覆盖的最小交互回归
- 运行页摘要能展示真实 backend/model routing

## Non-Goals

第一版不做：

- 密钥加密或系统凭据管理器
- 每个 stage 单独暴露模型选择
- 多 provider 并行 fallback
- 运行历史维度的 provider 统计
- 队列/worker 基础设施改造

## Expected Outcome

完成后，GUI 将不再固定落到 `heuristic`，而是能按用户在 GUI 中保存的 provider/base URL/model routing 启动真实 hosted backend 运行；同时 `clean` 的状态展示将与真实执行语义一致。
