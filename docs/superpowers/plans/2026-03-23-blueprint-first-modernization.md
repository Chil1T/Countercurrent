# Blueprint-First Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前数据库专用 transcript 流水线升级为 blueprint-first、CLI-first、GUI-ready 的通用教材网课知识库生成系统。

**Architecture:** 先引入运行时 `course_blueprint.json` 与 `runtime_state.json`，再让 pipeline、prompt、CLI 和 docs 全部围绕它工作。repo 内文档系统以 root `AGENTS.md` 为索引，`docs/` 负责承载 roadmap、架构、schema、runbook 与工作流说明。

**Tech Stack:** Python 3.11, argparse, unittest, JSON/Markdown runtime contracts

---

### Task 1: 引入 Blueprint Bootstrap 基础能力

**Files:**
- Create: `processagent/blueprint.py`
- Create: `processagent/bootstrap.py`
- Create: `tests/test_blueprint.py`

- [ ] **Step 1: 写失败测试，覆盖 TOC 驱动 blueprint 生成与缺 TOC 时的 AI 回退**
- [ ] **Step 2: 运行新增测试，确认旧实现失败**
- [ ] **Step 3: 实现 `metadata_resolver`、`toc_resolver`、`blueprint_builder` 的最小版本**
- [ ] **Step 4: 运行 blueprint 测试并修到通过**

### Task 2: 将 Pipeline 改为课程级输出与 blueprint-aware resume

**Files:**
- Modify: `processagent/pipeline.py`
- Modify: `processagent/testing.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: 写失败测试，覆盖 `out/courses/<course_id>` 布局、`runtime_state.json`、轻审校跳过**
- [ ] **Step 2: 运行这些测试，确认旧实现失败**
- [ ] **Step 3: 实现课程级目录布局、`runtime_state.json` 与 blueprint hash 校验**
- [ ] **Step 4: 实现 light review / conditional review**
- [ ] **Step 5: 运行 pipeline 相关测试并修到通过**

### Task 3: 重构 CLI 为子命令并加入 stage model routing

**Files:**
- Modify: `processagent/cli.py`
- Modify: `processagent/llm.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_backends.py`

- [ ] **Step 1: 写失败测试，覆盖 `build-blueprint`、`run-course`、`show-status` 与 stage model routing**
- [ ] **Step 2: 运行 CLI/后端测试，确认旧实现失败**
- [ ] **Step 3: 用子命令重构 CLI，同时尽量保留现有 provider 配置能力**
- [ ] **Step 4: 为 agent stage 增加模型路由解析与调用**
- [ ] **Step 5: 运行 CLI/后端测试并修到通过**

### Task 4: 重写 prompts 并建立 repo 文档系统

**Files:**
- Modify: `processagent/prompts/*.md`
- Create: `AGENTS.md`
- Create: `processagent/AGENTS.md`
- Create: `tests/AGENTS.md`
- Create: `docs/AGENTS.md`
- Create: `docs/README.md`
- Create: `docs/roadmap.md`
- Create: `docs/architecture/blueprint-first.md`
- Create: `docs/architecture/runtime-layout.md`
- Create: `docs/schemas/course_blueprint.md`
- Create: `docs/workstreams/*.md`
- Create: `docs/decisions/*.md`
- Create: `docs/runbooks/*.md`

- [ ] **Step 1: 更新 prompt 合同为 blueprint-first + light review**
- [ ] **Step 2: 创建 root `AGENTS.md` 索引与最小 nested `AGENTS.md`**
- [ ] **Step 3: 创建 roadmap / architecture / schema / runbook 文档骨架**
- [ ] **Step 4: 检查交叉链接与命名一致性**

### Task 5: 全量验证

**Files:**
- Modify: `PLANS.md`

- [ ] **Step 1: 运行 `python -m unittest discover -s tests -v`**
- [ ] **Step 2: 若仍有失败，最小化修复**
- [ ] **Step 3: 更新 `PLANS.md` 状态**
