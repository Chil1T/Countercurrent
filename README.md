# Countercurrent

`Countercurrent` 是一个面向“出版教材 + 对应网课录音/转写”的 `blueprint-first` 知识库生成工具。它会把章节 transcript 逆向整理成适合放进 NotebookLM 的教辅包，并保留中间结构化证据，便于断点续跑、审校和后续扩展。

## 当前能力

- `course_blueprint.json` 驱动的课程级运行时
- transcript -> 中间 JSON -> NotebookLM 教辅包 的多阶段流水线
- 默认 `resume`，并按 `blueprint_hash` 做 checkpoint 失效判断
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
- 本地测试: `python -m unittest discover -s tests -v`

## 目录结构

- [`processagent/`](C:/Users/ming/Documents/databaseleaning/processagent): pipeline、bootstrap、CLI、prompt
- [`tests/`](C:/Users/ming/Documents/databaseleaning/tests): `unittest` 测试
- [`docs/`](C:/Users/ming/Documents/databaseleaning/docs): roadmap、架构、schema、runbook、决策
- [`out/`](C:/Users/ming/Documents/databaseleaning/out): 运行时产物，不进版本控制

## CI

仓库已接入最小 `GitHub Actions CI`：

- 触发：`push`、`pull_request`
- 环境：`windows-latest`
- Python：`3.11`
- 校验命令：`python -m unittest discover -s tests -v`

## 文档入口

- [`AGENTS.md`](C:/Users/ming/Documents/databaseleaning/AGENTS.md): 仓库级索引与协作规则
- [`docs/README.md`](C:/Users/ming/Documents/databaseleaning/docs/README.md): 文档系统总览
- [`docs/architecture/blueprint-first.md`](C:/Users/ming/Documents/databaseleaning/docs/architecture/blueprint-first.md): blueprint-first 架构
- [`docs/schemas/course_blueprint.md`](C:/Users/ming/Documents/databaseleaning/docs/schemas/course_blueprint.md): blueprint schema
