# ReCurr

`ReCurr` 是一个面向“出版教材 + 对应网课录音/转写”的 `blueprint-first` 知识库生成工具。它会把章节 transcript 逆向整理成适合放进 NotebookLM 的教辅包，并保留中间结构化证据，便于断点续跑、审校和后续扩展。

## 当前能力

- `course_blueprint.json` 驱动的课程级运行时
- transcript -> 中间 JSON -> NotebookLM 教辅包 的多阶段流水线
- 默认 `resume`，并按 `blueprint_hash` 做 checkpoint 失效判断
- 本地优先的 Web GUI v1：输入、配置、运行、结果四页主流程
- GUI 已接通真实字幕文件上传、`LocalProcessRunner`、`SSE` 状态流、结果预览与 ZIP 导出
- 当前前端品牌名与浏览器标题统一为 `ReCurr`
- 多后端模型接入：
  - `openai`
  - `openai_compatible`
  - `anthropic`
  - `heuristic`
  - `stub`
- 最小 `GitHub Actions CI`

## 快速开始

1. 复制配置模板并填写本地密钥

```powershell
Copy-Item .env.example .env
```

2. 先生成课程 blueprint

```powershell
python -m processagent.cli build-blueprint `
  --book-title "数据库系统概论" `
  --input-dir .\captions `
  --output-dir .\out `
  --toc-file .\toc.txt
```

3. 再运行整套课程流水线

```powershell
python -m processagent.cli run-course `
  --book-title "数据库系统概论" `
  --input-dir .\captions `
  --output-dir .\out `
  --toc-file .\toc.txt `
  --backend openai_compatible
```

## 常用命令

- 构建 blueprint: `python -m processagent.cli build-blueprint ...`
- 执行课程: `python -m processagent.cli run-course ...`
- 断点续跑: `python -m processagent.cli resume-course ...`
- 查看状态: `python -m processagent.cli show-status ...`
- 清理课程产物: `python -m processagent.cli clean-course ...`
- GUI 本地联调一键启动: `.\start-gui-local.ps1`
- 本地测试: `python -m unittest discover -s tests -v`

## GUI 本地联调

默认一键启动前后端开发服务：

```powershell
.\start-gui-local.ps1
```

常见可选参数：

```powershell
.\start-gui-local.ps1 `
  -BackendPort 8100 `
  -FrontendPort 3100 `
  -SkipBackendInstall `
  -SkipFrontendInstall
```

脚本会执行以下本地联调编排：

- 默认清理 `8000/3000` 端口监听进程
- 后端日志写入 `out/_gui/backend-dev.log`
- 前端日志写入 `out/_gui/frontend-dev.log`
- 对 `http://127.0.0.1:<port>/healthz` 与 `http://127.0.0.1:<port>/courses/new/input` 做探活检查

## 目录结构

- [`processagent/`](processagent): pipeline、bootstrap、CLI、prompt
- [`server/`](server): FastAPI GUI 编排 API、产品模型与运行 adapter
- [`web/`](web): Next.js GUI 前端
- [`tests/`](tests): `unittest` 测试
- [`docs/`](docs): roadmap、架构、schema、runbook、决策
- [`out/`](out): 运行时产物，不进版本控制

## CI

仓库已接入最小 `GitHub Actions CI`：

- 触发：`push`、`pull_request`
- 环境：`windows-latest`
- Python：`3.11`
- 校验命令：`python -m unittest discover -s tests -v`

## 文档入口

- [`AGENTS.md`](AGENTS.md): 仓库级索引与协作规则
- [`docs/README.md`](docs/README.md): 文档系统总览
- [`docs/runbooks/gui-dev.md`](docs/runbooks/gui-dev.md): GUI 本地开发、验证与当前行为
- [`docs/architecture/blueprint-first.md`](docs/architecture/blueprint-first.md): blueprint-first 架构
- [`docs/schemas/course_blueprint.md`](docs/schemas/course_blueprint.md): blueprint schema
