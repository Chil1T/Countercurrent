# Plans

## 2026-04-01 Stitch V2 Frontend Migration

- Status: completed
- Goal: 以 Stitch 五页设计稿为目标界面，高保真迁移默认 GUI 页面骨架，同时完整保留当前输入、配置、运行、结果、空态与 preview 的真实功能和语义。

### Scope

- 建立 Stitch V2 共享设计系统与页面骨架
- 迁移 Overview、Input、Config、Run、Results 五页
- 保持产品空态与内部 preview 调试态边界
- 默认产品路由切到 V2
- 文档、批次索引与最终验证收口

### Execution Batches

1. 已完成：共享设计系统与壳层基础
2. 已完成：Overview 与产品空态
3. 已完成：Input V2
4. 已完成：Config V2
5. 已完成：Run V2
6. 已完成：Results V2
7. 已完成：默认路由切换与迁移债务清理
8. 已完成：文档、索引与最终验证

### Validation

- `node --experimental-strip-types --test web/tests/app-shell-branding.test.ts web/tests/app-shell-state.test.ts web/tests/overview-v2-workbench.test.ts web/tests/input-v2-workbench.test.ts web/tests/config-v2-workbench.test.ts web/tests/run-v2-workbench.test.ts web/tests/results-v2-workbench.test.ts web/tests/preview-mode.test.ts web/tests/artifacts-api.test.ts web/tests/input-workbench-ui.test.ts web/tests/config-workbench-view.test.ts web/tests/config-workbench-ui.test.ts web/tests/context-panel.test.ts web/tests/results-layout.test.ts web/tests/results-workbench-state.test.ts web/tests/results-refresh.test.ts web/tests/results-view.test.ts web/tests/results-tree-chapter-status.test.ts web/tests/results-interaction.test.ts web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts`
- `npm run lint`
- `npm run build`

## 2026-03-30 GUI Concurrency / Results UX

- Status: completed
- Goal: 重构运行页与结果页的信息架构，使 GUI 能正确表达多章节并发、课程级章节状态、过滤导出和稳定文件树交互，而不打破当前 runtime contract。

### Scope

- 运行页以章节卡片为主视图展示并发进度
- 结果页以课程级最新状态标记章节文件夹
- 导出区支持“仅已完成章节 / 仅最终产物”
- 文件树自动刷新但保留手动展开状态与当前选中文件
- 结果页左右布局在深层展开下保持稳定

### Execution Batches

1. 已完成：补课程级结果状态 read API
2. 已完成：运行页并发章节卡片视图
3. 已完成：结果页章节状态文件树
4. 已完成：过滤导出与稳定自动刷新
5. 已完成：结果页布局稳定化
6. 已完成：文档与验证收口

### Validation

- `python -m unittest server.tests.test_runs_api -v`
- `node --experimental-strip-types --test web/tests/artifacts-api.test.ts web/tests/results-view.test.ts web/tests/results-refresh.test.ts web/tests/results-layout.test.ts web/tests/run-workbench-layout.test.ts web/tests/run-workbench-chapter-progress.test.ts web/tests/results-workbench-state.test.ts`
- `python -m unittest server.tests.test_health server.tests.test_course_drafts_api server.tests.test_templates_api server.tests.test_runs_api server.tests.test_artifacts_api -v`
- `npm run lint`
- `npm run build`

## 2026-03-27 Runtime Concurrency / Retry / Export

- Status: completed
- Goal: 为非全局章节主流程引入多章节并发、provider 级限流、临时错误自动恢复，以及严格口径的章节级导出合同，为后续 UI 并发态展示提供稳定 backend/API 基线。

### Scope

- 引入 provider policy registry 与可覆盖默认值
- 将章节执行从课程级串行主循环中拆出，支持单 run 多章节并发
- 增加调用级 transient retry 与 run 级自动 `resume`
- 扩展 `runtime_state.json`、run API、artifact export 合同
- 同步 runbook、workstream 与 `processagent/AGENTS.md`

### Execution Batches

1. 已完成：provider policy registry 与配置来源优先级
2. 已完成：章节执行抽象与 checkpoint 安全边界
3. 已完成：双层并发控制（单 run + provider 全局）
4. 已完成：调用级 retry 与追责日志
5. 已完成：run 级自动 `resume` 与章节级状态合同
6. 已完成：严格口径章节导出与最终产物过滤
7. 已完成：文档、规则与验证收口

### Validation

- `python -m unittest tests.test_provider_policy tests.test_retry_policy tests.test_pipeline tests.test_cli -v`
- `python -m unittest server.tests.test_runs_api server.tests.test_artifacts_api -v`
- `python -m unittest discover -s tests -v`
- `npm run lint`
- `npm run build`

## 2026-03-25 GUI Config / Runflow Refinement

- Status: completed
- Goal: 收敛配置页与 Context 栏文案和展示逻辑，重构结果页文件树，并将 `resume` 调整为“流水线锁定、供应商配置刷新”，同时补齐并发治理与文档收口。

### Scope

- 将 Review 相关文案改成面向用户的表达
- 修正 Context 栏的素材完整度与后端/模型展示
- 将结果页改成带加载提示的层级文件树
- 将 `resume` 改成刷新 `provider/base_url/api_key/model/timeout`
- 明确高 provider 压力阶段并文档化当前串行执行 contract
- 在最后一步统一收口 runbook、AGENTS 和批次索引

### Execution Batches

1. 已完成：Context 栏显示语义修正
2. 已完成：配置页主路径收敛与文案优化
3. 已完成：结果页层级文件树与加载态
4. 已完成：`resume` 改为“流水线锁定、供应商配置刷新”
5. 已完成：高 provider 压力阶段审计与当前串行执行 contract
6. 已完成：文档、规则与验证收口

### Validation

- `python -m unittest discover -s tests -v`
- `python -m unittest server.tests.test_runs_api server.tests.test_artifacts_api -v`
- `npm run lint`
- `npm run build`

## 2026-03-25 Runtime Review / Cost Optimization

- Status: completed
- Goal: 将 runtime 链调整为默认不 review、无 quarantine、全局汇总手动触发，并补齐调用级 token 追责与两阶段 token 优化。

### Scope

- 默认关闭 `review`，保留课程默认值 + 单次运行覆盖
- 移除 `quarantine` 章节搬运机制
- 同课程名继续复用同一 `course_id`
- 将 `global/*` 汇总改为手动触发
- 为每次 LLM 调用落盘 token/耗时/错误追责信息
- 第一阶段先减调用次数，第二阶段再瘦 writer payload

### Execution Batches

1. 已完成：runtime contract 重构（默认关闭 review、移除 quarantine、全局汇总手动触发）
2. 已完成：GUI/RunService review 控制层与手动全局汇总入口
3. 已完成：调用级 token 追责落盘
4. 已完成：模板裁剪 writers 与 writer payload 瘦身
5. 已完成：runbook、AGENTS 与验证收口

### Validation

- `python -m unittest discover -s tests -v`
- `python -m unittest server.tests.test_runs_api server.tests.test_artifacts_api -v`
- `npm run lint`
- `npm run build`

## 2026-03-24 Agent Contract Refactor

- Status: completed
- Goal: 重构 pipeline 的 agent 输出合同，把长文本产物从大 JSON stage 拆成 planner + 多个 text writer，并让三种模板映射到统一的 writer profile。

### Scope

- 保留结构化小输出 stage 的 JSON 合同
- 拆分 `compose_pack` 为 planner + 5 个 writer
- 拆分 `canonicalize` 为 2 个 writer
- 引入三种模板的统一 profile 映射
- 更新 checkpoint / resume / invalidation 语义

### Execution Batches

1. 已完成：新 prompt surface、`generate_text` contract、stage 名和 compose/canonicalize writer 设计
2. 已完成：pipeline 侧 compose/canonicalize 拆分与 GUI stage 轨道映射
3. 已完成：模板继续映射到既有 `target_output`，并接入 writer profile 视图
4. 已完成：runbook、workstream 文档与验证收口

### Validation

- `python -m unittest tests.test_pipeline -v`
- `python -m unittest tests.test_cli -v`
- `python -m unittest discover -s tests -v`

## 2026-03-24 GUI Real Backend Routing

- Status: completed
- Goal: 为 GUI 接通真实 hosted backend 配置、两层模型路由与本地配置持久化，并修正 `clean` 的运行状态语义。

### Scope

- 新增 GUI 本地 runtime config 存储
- 支持 `openai`、`openai_compatible`、`anthropic`
- 支持全局默认值 + 课程级覆盖
- 支持 `simple_model` / `complex_model` 两层模型路由
- 将 GUI 配置解析成真实 CLI hosted backend 参数
- 修正 `clean` 后运行状态与运行页摘要

### Execution Batches

1. 已完成：GUI runtime config 模型、本地配置存储、课程配置扩展
2. 已完成：`RunService` / `CourseRunSpec` / CLI adapter hosted backend 接线
3. 已完成：配置页 provider/model UI 与运行页摘要更新
4. 已完成：runbook、批次索引与验证收口

### Validation

- `python -m unittest discover -s tests -v`
- `python -m unittest server.tests.test_health server.tests.test_templates_api server.tests.test_runs_api -v`
- `npm run lint`
- `npm run build`

## 2026-03-23 GUI Web Product v1

- Status: completed
- Goal: 为 `databaseleaning` 建立本地优先、前后端分离、可继续部署的 Web GUI，覆盖输入、配置、运行、结果四页主流程。

### Scope

- 建立 `web/` 前端壳层与四页流程
- 建立 `server/` FastAPI 编排 API
- 以 application/adapter 边界封装现有 CLI/runtime
- 输入页支持课程链接、字幕与教材名
- 配置页支持模板与参数编辑
- 运行页支持阶段状态与 resumable 反馈
- 结果页支持文件树、预览、review 摘要与 ZIP 导出

### Execution Batches

1. 已完成：前端壳层、后端骨架、输入页、配置页、真实 runner、结果页、SSE、resume/clean、日志面板、多字幕资产输入、真实文件上传
2. 已完成：浏览器级主链路验证（输入 -> 配置 -> 运行 -> 结果）
3. 已完成：更细粒度日志流
4. 已完成：GUI 文档收束与最终验证

### Validation

- Python backend tests
- Frontend lint/typecheck/build or equivalent smoke verification

## 2026-03-23 Blueprint-First Modernization

- Status: completed
- Goal: 将当前数据库专用 transcript 流水线升级为 blueprint-first、CLI-first、GUI-ready 的通用教材网课知识库生成系统。

### Scope

- 引入 `course_blueprint.json` 与 `runtime_state.json`
- 新增 bootstrap 阶段与课程级输出布局
- 将 resume 升级为 blueprint-aware
- 将 reviewer 改为轻审校/条件触发
- 将 CLI 重构为子命令
- 建立以 root `AGENTS.md` 为索引的 repo 文档系统

### Execution Batches

1. 已补测试：blueprint/bootstrap、course-scoped 输出、CLI 子命令、stage model routing
2. 已实现运行时蓝图与 bootstrap
3. 已改造 pipeline 的课程级布局与 checkpoint 语义
4. 已重构 CLI 与配置解析
5. 已补齐 `AGENTS.md` 与 `docs/`

### Validation

- `python -m unittest discover -s tests -v`
