# Runtime Concurrency / Retry / Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add chapter-level concurrency, provider-aware throttling, transient-error recovery, and strict completed-chapter export to the non-global runtime without breaking existing checkpoint and resume semantics.

**Architecture:** Keep `course_blueprint.json` and `runtime_state.json` as the runtime source of truth, but split orchestration responsibilities so course-level scheduling, per-chapter execution, provider policy, and retry/resume policy are isolated. Preserve single-course single-run locking, keep single-chapter stages serial, and expose new chapter-level status fields through the server API so a later UI pass can consume stable contracts instead of inferring state from files.

**Tech Stack:** Python, FastAPI, Pydantic, existing `processagent` CLI/runtime, Python `unittest`, minimal TypeScript API type sync for frontend compatibility.

---

## File Map

### Runtime Core

- Create: `processagent/provider_policy.py`
- Create: `processagent/retrying_llm.py`
- Create: `processagent/chapter_execution.py`
- Modify: `processagent/pipeline.py`
- Modify: `processagent/llm.py`
- Modify: `processagent/cli.py`
- Test: `tests/test_provider_policy.py`
- Test: `tests/test_retry_policy.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_cli.py`

### Server / API

- Modify: `server/app/models/gui_runtime_config.py`
- Modify: `server/app/adapters/gui_config_store.py`
- Modify: `server/app/adapters/cli_runner.py`
- Modify: `server/app/adapters/runtime_reader.py`
- Modify: `server/app/application/runs.py`
- Modify: `server/app/application/artifacts.py`
- Modify: `server/app/api/artifacts.py`
- Modify: `server/app/models/run_session.py`
- Test: `server/tests/test_runs_api.py`
- Test: `server/tests/test_artifacts_api.py`

### Frontend Compatibility

- Modify: `web/lib/api/runs.ts`
- Modify: `web/lib/api/artifacts.ts`
- Test: `web/tests/artifacts-api.test.ts`

### Documentation

- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/workstreams/blueprint-runtime.md`
- Modify: `processagent/AGENTS.md`
- Modify: `PLANS.md`

---

### Task 1: 建立 provider policy registry 与配置来源优先级

**Files:**
- Create: `processagent/provider_policy.py`
- Modify: `server/app/models/gui_runtime_config.py`
- Modify: `server/app/adapters/gui_config_store.py`
- Modify: `processagent/cli.py`
- Test: `tests/test_provider_policy.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: 写出 provider policy 失败测试**

覆盖以下行为：
- 内置 provider 默认值覆盖 `openai`、`openai_compatible`、`anthropic`、`heuristic`、`stub`
- 优先级为 `CLI override > GUI/runtime config > builtin default`
- policy 字段至少包含 `max_concurrent_per_run`、`max_concurrent_global`、`max_call_attempts`、`max_resume_attempts`

- [ ] **Step 2: 运行测试确认 registry 尚不存在**

Run:
- `python -m unittest tests.test_provider_policy -v`
- `python -m unittest tests.test_cli -v`

Expected: FAIL，证明当前还没有独立 provider policy registry，也没有相应 CLI / config 解析。

- [ ] **Step 3: 实现最小 provider policy 模块**

在 `processagent/provider_policy.py` 中定义：

```python
@dataclass(frozen=True)
class ProviderExecutionPolicy:
    provider: str
    max_concurrent_per_run: int
    max_concurrent_global: int
    transient_http_statuses: tuple[int, ...]
    max_call_attempts: int
    max_resume_attempts: int
```

并提供：
- 内置默认表
- config 合并函数
- CLI override 合并函数

在 `server/app/models/gui_runtime_config.py` 中补 provider policy 设置模型。

- [ ] **Step 4: 接通 CLI 参数到 policy 解析**

在 `processagent/cli.py` 中新增保守覆盖面：
- `--max-concurrent-per-run`
- `--max-concurrent-global`
- `--max-call-attempts`
- `--max-resume-attempts`

只为 `run-course` / `resume-course` / `build-global` 接线必要的 policy 参数，不给无关子命令加噪音。

- [ ] **Step 5: 重新运行测试**

Run:
- `python -m unittest tests.test_provider_policy -v`
- `python -m unittest tests.test_cli -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add processagent/provider_policy.py processagent/cli.py server/app/models/gui_runtime_config.py server/app/adapters/gui_config_store.py tests/test_provider_policy.py tests/test_cli.py
git commit -m "feat: add provider execution policy registry"
```

### Task 2: 抽出章节执行单元并保持 checkpoint 语义稳定

**Files:**
- Create: `processagent/chapter_execution.py`
- Modify: `processagent/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: 写出章节执行与 checkpoint 失败测试**

覆盖以下行为：
- 单章节内部 stage 仍按既有顺序串行
- 已完成 step 不会因章节并发而被重复执行
- 同一章节写入 `runtime_state.json` 时不会丢失其他章节状态

- [ ] **Step 2: 运行 pipeline 测试确认旧实现仍是课程级串行**

Run: `python -m unittest tests.test_pipeline -v`

Expected: FAIL，证明当前章节执行、状态更新和课程级 orchestrator 仍耦合在 `pipeline.py` 的串行主循环里。

- [ ] **Step 3: 实现章节执行抽象**

在 `processagent/chapter_execution.py` 中创建：

```python
class ChapterExecutionPlanner: ...
class ChapterWorker: ...
class RuntimeStateMutationGuard: ...
```

职责要求：
- planner 只决定“哪些章节、哪些 step 需要跑”
- worker 只跑单章节
- runtime state 写入通过单一保护入口完成

- [ ] **Step 4: 将 `PipelineRunner` 改成课程级 orchestrator**

在 `processagent/pipeline.py` 中：
- 保留对外入口与既有 contract
- 将单章节工作委托给 `ChapterWorker`
- 保持 `build-global` 仍为单独串行路径

- [ ] **Step 5: 重新运行 pipeline 测试**

Run: `python -m unittest tests.test_pipeline -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add processagent/chapter_execution.py processagent/pipeline.py tests/test_pipeline.py
git commit -m "refactor: split chapter execution from course orchestration"
```

### Task 3: 为非全局章节主流程接入双层并发控制

**Files:**
- Modify: `processagent/provider_policy.py`
- Modify: `processagent/chapter_execution.py`
- Modify: `processagent/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: 写出章节并发调度失败测试**

覆盖以下行为：
- 同一次 run 内可并发执行多个章节
- 单 run 并发数受 policy 限制
- 全服务 provider 并发池限制不同 run 的 provider 调用总量
- 同一 `course_id` 仍禁止多个活跃 run

- [ ] **Step 2: 运行测试确认旧实现不支持章节并发**

Run: `python -m unittest tests.test_pipeline -v`

Expected: FAIL，证明当前 run 内章节循环仍是串行，且没有 provider 级 semaphore。

- [ ] **Step 3: 实现单 run 与全局 provider 限流**

在 runtime 层加入：
- 单 run chapter worker 调度器
- provider 全局 semaphore registry
- 对 hosted stage 获取 provider permit 的统一入口

不要让单章节内部 writer stage 并发化。

- [ ] **Step 4: 补充并发安全断言**

确保：
- hosted step 释放 permit
- 失败路径也释放 permit
- `heuristic` / `stub` 在 registry 下行为一致

- [ ] **Step 5: 重新运行 pipeline 测试**

Run: `python -m unittest tests.test_pipeline -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add processagent/provider_policy.py processagent/chapter_execution.py processagent/pipeline.py tests/test_pipeline.py
git commit -m "feat: add provider-aware chapter concurrency"
```

### Task 4: 增加调用级 transient retry 与追责日志

**Files:**
- Create: `processagent/retrying_llm.py`
- Modify: `processagent/llm.py`
- Modify: `processagent/pipeline.py`
- Modify: `processagent/provider_policy.py`
- Test: `tests/test_retry_policy.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: 写出 transient retry 失败测试**

覆盖以下行为：
- 仅 transient HTTP 状态码与网络异常触发 retry
- 默认最多 3 次尝试
- 永久错误直接失败
- 每次 retry 都记录原因、次数、结果

- [ ] **Step 2: 运行测试确认当前 backend 不区分 transient / permanent**

Run:
- `python -m unittest tests.test_retry_policy -v`
- `python -m unittest tests.test_pipeline -v`

Expected: FAIL，证明当前错误只会直接抛出 `RuntimeError`，没有统一 retry 包装层。

- [ ] **Step 3: 实现 `RetryingLLMBackend`**

在 `processagent/retrying_llm.py` 中封装：

```python
class RetryingLLMBackend:
    def generate_json(...): ...
    def generate_text(...): ...
```

要求：
- 包装现有 backend
- 按 policy 做指数退避
- 把每次 attempt 元数据写回调用方可消费结构

- [ ] **Step 4: 把 retry metadata 写入 runtime 与 `llm_calls.jsonl`**

在 `processagent/pipeline.py` 中：
- step 级落盘 `attempt_count`、`last_error_kind`、`retry_history`
- `runtime/llm_calls.jsonl` 追加 retry attempt 结果

- [ ] **Step 5: 重新运行重试与 pipeline 测试**

Run:
- `python -m unittest tests.test_retry_policy -v`
- `python -m unittest tests.test_pipeline -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add processagent/retrying_llm.py processagent/llm.py processagent/pipeline.py processagent/provider_policy.py tests/test_retry_policy.py tests/test_pipeline.py
git commit -m "feat: add transient retry policy for llm calls"
```

### Task 5: 接入 run 级自动 `resume` 与章节级实时状态合同

**Files:**
- Modify: `server/app/application/runs.py`
- Modify: `server/app/adapters/cli_runner.py`
- Modify: `server/app/adapters/runtime_reader.py`
- Modify: `server/app/models/run_session.py`
- Test: `server/tests/test_runs_api.py`

- [ ] **Step 1: 写出 run 级自动恢复失败测试**

覆盖以下行为：
- 调用级 retry 耗尽但被标为 transient 的 run 会自动进入 `resume-course`
- 自动 `resume` 达到上限后停在失败态
- `chapter_progress[]` 能同时显示多个章节状态
- 课程级 stage 轨道仍兼容旧前端

- [ ] **Step 2: 运行后端测试确认当前 run 状态仍只有课程级聚合**

Run: `python -m unittest server.tests.test_runs_api -v`

Expected: FAIL，证明当前 `RunSession` 没有章节级状态，也没有自动 `resume` 编排。

- [ ] **Step 3: 扩展运行态模型**

在 `server/app/models/run_session.py` 中新增：

```python
class ChapterProgress(BaseModel):
    chapter_id: str
    status: str
    current_step: str | None = None
    completed_step_count: int = 0
    total_step_count: int = 0
    export_ready: bool = False
```

并将其挂到 `RunSession.chapter_progress`。

- [ ] **Step 4: 在 `RunService` 中实现自动 `resume` 与状态映射**

在 `server/app/application/runs.py` / `server/app/adapters/runtime_reader.py` 中：
- 读取章节级 step metadata
- 将 transient failure 与 permanent failure 分开
- 命中策略时自动调起 `resume-course`
- 返回 `chapter_progress[]`

- [ ] **Step 5: 重新运行 run API 测试**

Run: `python -m unittest server.tests.test_runs_api -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add server/app/application/runs.py server/app/adapters/cli_runner.py server/app/adapters/runtime_reader.py server/app/models/run_session.py server/tests/test_runs_api.py
git commit -m "feat: add chapter progress and automatic resume"
```

### Task 6: 支持严格口径的章节级导出与最终产物过滤

**Files:**
- Modify: `server/app/application/artifacts.py`
- Modify: `server/app/api/artifacts.py`
- Modify: `server/app/adapters/runtime_reader.py`
- Modify: `web/lib/api/artifacts.ts`
- Modify: `web/lib/api/runs.ts`
- Test: `server/tests/test_artifacts_api.py`
- Test: `web/tests/artifacts-api.test.ts`

- [ ] **Step 1: 写出导出过滤失败测试**

覆盖以下行为：
- 默认整课 ZIP 仍兼容
- `completed_chapters_only=true` 仅导出 `export_ready=true` 章节
- `final_outputs_only=true` 仅导出 `notebooklm/*`
- 未完成章节即使已有部分文件也不会被误导出

- [ ] **Step 2: 运行测试确认当前导出仍是无过滤全量 ZIP**

Run:
- `python -m unittest server.tests.test_artifacts_api -v`
- `node --test --experimental-strip-types web\\tests\\artifacts-api.test.ts`

Expected: FAIL，证明当前导出接口不接受过滤维度，前端 API 也没有相应类型。

- [ ] **Step 3: 实现 artifacts 过滤逻辑**

在 `server/app/application/artifacts.py` / `server/app/api/artifacts.py` 中：
- 为 export 增加过滤参数
- 基于章节 `export_ready` 判定可导出范围
- 增加仅最终产物导出路径

- [ ] **Step 4: 同步前端 API 类型**

在 `web/lib/api/artifacts.ts` 和必要时 `web/lib/api/runs.ts` 中：
- 增加过滤参数 builder
- 扩展新返回字段类型

不做结果页交互改造，只做 API 契约同步，保证构建通过。

- [ ] **Step 5: 重新运行导出测试**

Run:
- `python -m unittest server.tests.test_artifacts_api -v`
- `node --test --experimental-strip-types web\\tests\\artifacts-api.test.ts`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add server/app/application/artifacts.py server/app/api/artifacts.py server/app/adapters/runtime_reader.py web/lib/api/artifacts.ts web/lib/api/runs.ts server/tests/test_artifacts_api.py web/tests/artifacts-api.test.ts
git commit -m "feat: add completed chapter export filters"
```

### Task 7: 文档、规则与全量验证收口

**Files:**
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `docs/runbooks/run-course.md`
- Modify: `docs/workstreams/blueprint-runtime.md`
- Modify: `processagent/AGENTS.md`
- Modify: `PLANS.md`

- [ ] **Step 1: 更新运行 contract 文档**

把以下内容写入 runbook / workstream：
- 非全局章节 run 现已支持多章节并发
- provider registry 默认值、覆盖顺序与边界
- 调用级 retry 与 run 级自动 `resume` 的职责划分
- 章节级 `export_ready` 严格口径
- 导出过滤参数与兼容路径

- [ ] **Step 2: 更新协作规则**

在 `processagent/AGENTS.md` 中改写“当前单次 run 串行”的旧规则，明确：
- 章节间可并发
- 单章节内 stage 仍串行
- `build-global` 仍串行

- [ ] **Step 3: 更新批次索引**

在 `PLANS.md` 中新增本计划批次，列出：
- runtime contract / provider registry
- 章节并发
- retry / auto-resume
- export / API contract
- 文档收口

- [ ] **Step 4: 运行全量验证**

Run:
- `python -m unittest tests.test_provider_policy tests.test_retry_policy tests.test_pipeline tests.test_cli -v`
- `python -m unittest server.tests.test_runs_api server.tests.test_artifacts_api -v`
- `python -m unittest discover -s tests -v`
- `npm run lint`
- `npm run build`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/runbooks/gui-dev.md docs/runbooks/run-course.md docs/workstreams/blueprint-runtime.md processagent/AGENTS.md PLANS.md
git commit -m "docs: document concurrent runtime and export contract"
```
