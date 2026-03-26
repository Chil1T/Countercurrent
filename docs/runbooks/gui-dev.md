# GUI Development Runbook

## Scope

本 runbook 说明 `databaseleaning` GUI v1 的本地开发与最小验证方式。

## Components

- `web/`: Next.js 前端
- `server/`: FastAPI 编排 API

## GUI Runtime Preconditions

要从 GUI 成功启动一次课程运行，当前最小前置条件是：

- 已生成 `CourseDraft`
- 已提供非空白的 `book_title`
- 已提供至少一个可落盘的字幕/转录输入
- 后端已为该草稿生成 GUI draft input 目录

当前 v1 的最小可执行输入是：

- 教材名
- 字幕文本

字幕文本会被写入：

```text
out/_gui/drafts/<draft_id>/input/chapter-01.md
```

`RunService` 只有在该输入目录存在至少一个 `.md` transcript 时，才会允许创建或恢复运行。

多字幕输入当前还要求文件名在规范化后保持唯一；如果两个上传文件在去掉路径并标准化后落到同一文件名，API 会直接拒绝草稿创建，而不是静默覆盖其一。

## Run State Model

GUI 运行页当前采用下面这组产品状态：

- `created`: 已创建运行会话，尚未拿到稳定 runner 状态
- `running`: 本地 runner 正在执行 `run-course` 或 `resume-course`
- `failed`: runner 失败，允许用户查看错误并尝试 `resume`
- `completed`: 运行完成，可进入结果页
- `cleaned`: 已执行 `clean-course`，阶段轨道应重置为 `pending`

界面规则：

- `cleaned` 不保留旧的阶段完成态
- `SSE` 断线只显示告警，不把整个运行页切成失败态
- `resume` / `clean` 只在当前 run 不处于 `running` 时允许触发
- 阶段轨道以下面的运行时合同为准：`course_blueprint.json`、`runtime_state.json`
- `resume` 会继续当前 run 已冻结的流水线身份：`target_output`、`review_enabled`、`review_mode` 与 stage graph
- `resume` 会重新读取当前 provider routing：`provider`、`base_url`、`api_key`、`simple_model`、`complex_model`、`timeout_seconds`
- 如果要改模板或 Review 策略，请创建新的 run，而不是复用旧 run

## GUI Runtime Config

GUI 当前支持以下执行后端：

- `heuristic`
- `openai`
- `openai_compatible`
- `anthropic`

本地 GUI 默认配置文件位于：

```text
%USERPROFILE%\.codex\databaseleaning\gui-config.json
```

当前版本的存储方式是：

- 配置文件保存在仓库外
- provider API key 以本地明文方式保存
- API key 只在具体 run 子进程启动时注入对应环境变量
- 不会修改 FastAPI 服务进程的全局环境变量

## Runtime Config Resolution

GUI 当前对 runtime config 的解析顺序是：

1. 课程级覆盖
2. GUI provider 默认值
3. CLI 默认值

当前已接入 runtime 的配置包括：

- `provider`
- `base_url`
- `simple_model`
- `complex_model`
- `timeout_seconds`
- `review_mode`
- `review_enabled`
- `template -> target_output`

当前仍未接入 `run-course` runtime contract 的配置包括：

- `content_density`
- `export ZIP`

### timeout_seconds

`timeout_seconds` 的当前语义是：

- 只控制单次 hosted LLM HTTP 请求超时
- 不控制整次课程 run 的总耗时
- 不控制前端页面等待时间
- 在 `heuristic` backend 下基本无意义

覆盖优先级是：

1. 课程级 `timeout_seconds`
2. provider 默认 `timeout_seconds`
3. CLI 默认值 `300`

当 `timeout_seconds <= 0` 时，API 层会直接拒绝创建 run。

## Model Routing

GUI 当前采用两层模型路由：

- `simple_model`
  - `blueprint_builder`
  - `curriculum_anchor`
  - `build_global_glossary`
  - `build_interview_index`
- `complex_model`
  - `gap_fill`
  - `pack_plan`
  - `write_lecture_note`
  - `write_terms`
  - `write_interview_qa`
  - `write_cross_links`
  - `review`

`base_url` 会在 API 层按 CLI 合同做规范化；缺 key、非法 `base_url`、非法 timeout 会直接拒绝创建 run。

## Current Runtime Shape

当前 GUI 运行分成两条路径：

- 章节主流程
  - `build_blueprint`
  - `ingest`
  - `curriculum_anchor`
  - `gap_fill`
  - `pack_plan`
  - `active writers`
  - 可选 `review`
- 全局汇总流程
  - `build_global_glossary`
  - `build_interview_index`

说明：

- GUI 的“启动 / 继续运行”默认走章节主流程
- GUI 的“更新全局汇总”会单独创建一个 `run_kind = global`
- `review` 默认关闭；可以由课程默认值打开，也可以在单次 run 时覆盖
- `quarantine` 已移除；review 只产出提示报告，不再隔离章节
- 单次章节 run 当前是串行执行：
  - transcript 章节循环串行
  - 单章 stage 串行
  - active writers 串行
- provider 压力主要来自 hosted writer/review/global 阶段，以及多 run 并发，不来自单次 run 内部 fan-out
- 同一个 `course_id` 当前只允许一个活跃 run；当某门课已有 `running` 的章节 run 或 global run 时，GUI/API 会拒绝为该课程再启动新的 run，避免并发写坏同一份 `out/courses/<course_id>` runtime。

## Writer Profile

当前模板会直接裁剪 writer 数量：

- `lecture-deep-dive`
  - `write_lecture_note`
  - `write_terms`
  - `write_cross_links`
- `standard-knowledge-pack`
  - `write_lecture_note`
  - `write_terms`
  - `write_interview_qa`
  - `write_cross_links`
  - `write_open_questions`
- `interview-focus`
  - `write_lecture_note`
  - `write_terms`
  - `write_interview_qa`
  - `write_cross_links`

## Internal Token Logs

每次 LLM 调用的追责日志会写到：

```text
out/courses/<course_id>/runtime/llm_calls.jsonl
```

这份日志仅用于内部调试，不在 GUI 展示。

## Local Commands

### One-Click Local Start

仓库根目录现在提供一键本地联调脚本：

```powershell
.\start-gui-local.ps1
```

默认行为：

- 清理 `3000/8000` 监听端口
- 后端使用 `python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000`
- 前端使用 `npx next dev --hostname 127.0.0.1 --port 3000`
- 日志写入 `out/_gui/backend-dev.log` 与 `out/_gui/frontend-dev.log`
- 轮询 `healthz` 与 `/courses/new/input`，只有两者都返回 `200` 才算启动成功

常用可选参数：

```powershell
.\start-gui-local.ps1 `
  -BackendPort 8100 `
  -FrontendPort 3100 `
  -SkipBackendInstall `
  -SkipFrontendInstall `
  -NoCleanPorts `
  -HealthTimeoutSeconds 90
```

说明：

- 默认 `WorkspaceRoot` 为脚本所在仓库根目录
- `SkipBackendInstall` / `SkipFrontendInstall` 适合依赖已安装的重复启动
- `NoCleanPorts` 适合你明确知道现有 `3000/8000` 服务应保留时使用
- `DryRun` 只打印将执行的命令、日志路径和探活地址，不真正启动进程

### Frontend

```powershell
cd web
npm install
npm run lint
npm run build
npx next dev --hostname 127.0.0.1 --port 3000
```

### Backend

```powershell
python -m pip install -r server/requirements.txt
python -m unittest server.tests.test_health server.tests.test_course_drafts_api server.tests.test_templates_api server.tests.test_runs_api server.tests.test_artifacts_api -v
python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000
```

## Service Lifecycle

本项目本地联调最容易失败的地方，不是启动命令本身，而是：

- 旧进程仍占着 `3000/8000`
- 窗口被手动关掉后服务直接消失
- 命令返回了，但端口其实还没开始监听

因此，`启动成功` 的标准必须是：**端口监听 + HTTP 探活返回 200**，不是“命令看起来执行了”。

### Standard Stop

先按端口清理旧服务：

```powershell
$ports = 3000,8000
foreach ($port in $ports) {
  $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  foreach ($conn in $conns) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
  }
}
```

### Standard Start

前台看日志时，分别开两个终端：

后端：

```powershell
python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd web
npx next dev --hostname 127.0.0.1 --port 3000
```

### Background Start

需要后台常驻时，不要依赖 `cmd /k`。更稳的是输出到日志文件：

后端：

```powershell
Start-Process cmd.exe -ArgumentList '/c','python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000 > out\_gui\backend-dev.log 2>&1' -WorkingDirectory (Get-Location)
```

前端：

```powershell
Start-Process cmd.exe -ArgumentList '/c','npx next dev --hostname 127.0.0.1 --port 3000 > ..\out\_gui\frontend-dev.log 2>&1' -WorkingDirectory (Join-Path (Get-Location) 'web')
```

说明：

- `cmd /k` 适合人工盯日志，但关窗口就会停服务
- `cmd /c ... > log 2>&1` 更适合后台常驻
- 不要把 `Start-Process` 的 `RedirectStandardOutput` 和 `RedirectStandardError` 指到同一个文件；PowerShell 会直接报错

### Standard Health Checks

启动后必须探活：

后端：

```powershell
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/healthz).StatusCode
```

前端：

```powershell
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:3000/courses/new/input).StatusCode
```

预期都返回 `200`。

### Standard Restart

推荐固定流程：

1. 先执行 `Standard Stop`
2. 再执行 `Standard Start` 或 `Background Start`
3. 最后执行 `Standard Health Checks`

如果探活失败，再去看日志，不要直接假设服务已经起来。

### Local Logs

后台模式默认日志位置：

```text
out/_gui/backend-dev.log
out/_gui/frontend-dev.log
```

优先从这里看：

- 端口占用
- 依赖缺失
- dev server 没真正监听
- 启动命令被窗口关闭打断

## Browser QA

当需要做浏览器级交互核查时，优先复用本地 Playwright 调试：

- 启动 `server` 与 `web` 本地服务
- 用 `http://127.0.0.1:3000/courses/new/input` 进入输入页
- 至少覆盖一次主链路：
  - 创建包含多个字幕资产或本地上传文件的草稿
  - 跳转配置页并保存模板
  - 启动运行
  - 进入结果页，确认文件树、预览和 reviewer/export 区域可见
- 如果只是静态校验，不必默认启用 Playwright；仅在交互或视觉状态需要验证时使用

当进入人工测试批次时，额外补一条 `clean-browser baseline`：

- 在服务启动并通过探活后，再用 `chrome-devtools-mcp` 打开目标页面
- 把这一步视为“干净浏览器基线”，用于区分：
  - 仓库代码问题
  - 本地浏览器扩展注入
  - 缓存、会话、缩放等环境差异
- 推荐顺序是：
  - 先做 `Standard Health Checks`
  - 再用 `chrome-devtools-mcp` 打开目标页面
  - 最后由用户在自己的常用浏览器里做真实体验验收
- 如果 `chrome-devtools-mcp` 中无法复现，而用户本地浏览器能复现，优先怀疑：
  - 浏览器扩展
  - 本地缓存
  - 用户浏览器特有登录态或会话状态

这条基线用于人工验收与远程协同排障，不替代用户自己的真实浏览器测试。

## Current Notes

- 输入页当前的最小可执行输入是：教材名 + 字幕文本；字幕会落盘到 GUI draft input 目录，供 `run-course` 使用。
- GUI 草稿在生成 `course_id` 前会先 `strip()` 教材名，避免用户输入前后空格时，GUI 指向的课程目录和 pipeline 真正写入的目录不一致。
- `runs` 已接通本地 `LocalProcessRunner`，通过 `runtime_state.json` 和 `course_blueprint.json` 映射阶段状态。
- 运行页顶部的 `View` 只表示当前页面类型；真正的运行状态以“运行总状态”和阶段轨道为准。
- 当前默认执行后端仍可设为 `heuristic`；只有当 GUI 默认值或课程覆盖显式切到 hosted provider，GUI 才会真正调用外部 AI 服务。
- 配置页的“启动 / 继续运行”遵循 CLI 的 resume 语义：同一 `course_id` 下已有且仍然有效的 checkpoint 会被复用，不默认强制全量重跑。
- `resume` 会继续同一个 run 的冻结流水线身份；如果你修改了 provider/model/base_url/key/timeout，恢复时会读取新 routing；如果你修改了模板或 Review 策略，请创建新的 run。
- 运行页已接入 `SSE` 事件流，并提供 `resume` / `clean` 控制动作。
- 运行页右侧已接入日志面板：先拉取 log preview，再通过 `run.log` 事件流增量追加。
- 运行页摘要卡现在会明确显示 `backend`、`hosted/heuristic`、`simple_model`、`complex_model`、`review_mode`、`target_output`，用于区分“页面已打开”和“runtime 实际采用的配置”。
- `RunSession` 当前会持久化到 `out/_gui/runs/<run_id>/session.json`，后端重启后，已存在的 run 页面不再直接因内存态丢失而 404。
- 历史 run 的 `process.log` 当前也支持在后端重启后恢复读取；日志面板不再依赖 runner 的内存 snapshot 才能显示旧日志。
- `runtime_state.json` 当前会额外持久化 `run_identity`，用于恢复时锁定 `review_enabled`、`review_mode` 和 `target_output`。
- 结果页已接通 artifacts tree、文件预览、review 摘要和 ZIP 导出。
- 结果页文件树当前按 `章节 -> 最终产物 / 中间数据 -> 文件` 分层；若对应 run 尚未完成，会显示“文件仍在生成中”的提示，而不是把空树误判为失败。
- 如果结果页在 run 仍未完成时已经打开，artifact tree 与 review summary 当前会在 `run.update` 推进时自动刷新，不需要手动刷新页面。
- FastAPI 默认以仓库根目录推导 `workspace_root` 与 `out/`，结果页不再依赖 uvicorn 是从哪个当前目录启动的。
- 左侧 `运行` / `结果` 导航和首页入口不再使用 `demo` 占位路由；只有真实 `run_id` / `course_id` 已绑定时才会启用对应入口。
- 当从运行页或结果页返回输入/配置页时，shell 现在会继续保留 `draftId/runId/courseId`，避免 sidebar 把 `运行` / `结果` 重新打回 `pending`。
- 输入页当前已支持真实字幕文件上传，以及多个文件感知的手工字幕资产条目。
- 当前 GUI 配置里，下面这些已经真实进入 runtime：
  - `provider`
  - `base_url`
  - `simple_model`
  - `complex_model`
  - `timeout_seconds`
  - `review_enabled`
  - `template` -> `policy.target_output`
  - `review_mode` -> `policy.review_mode`
- `build-blueprint` / `run-course` 当前会把 `simple_model` 中映射给 `blueprint_builder` 的 override 直接用于 blueprint 生成阶段，不再回落到 provider 默认模型。
- 如果草稿尚未保存模板配置，GUI 运行默认按 `interview_knowledge_base` 解释章节 writer 集合与阶段轨道，不再错误回落到 `standard_knowledge_pack`。
- `clean-course` 如果在运行中遇到后端重启，状态恢复会优先依据课程 runtime 目录是否已删除来判断 `cleaned`，避免清理完成后仍长期显示 `running`。
- 运行状态恢复当前会以 `runtime_state.json` 里的实际 chapter scopes 为准，而不是 blueprint 中声明的章节总数；当 TOC 章节数和实际输入章节数不一致时，重启后也不会因为完成计数永远达不到 blueprint 总数而卡在 `running`。
- `content_density` 和 `export ZIP` 仍然是产品层配置，还没有进入 `run-course` 的 runtime contract。
- checkpoint 有效性现在同时受 `blueprint_hash` 和 pipeline signature 约束；当 pipeline/runtime contract 变更时，旧产物会在下一次运行时自动失效并重跑。
- 同课程名当前继续复用同一 `course_id`；新章节会追加到同一课程目录。
