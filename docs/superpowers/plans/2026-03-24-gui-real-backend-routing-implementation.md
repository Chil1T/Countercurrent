# GUI Real Backend Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 GUI 接通真实 hosted backend 配置、两层模型路由与本地配置持久化，并修正 `clean` 的运行状态语义。

**Architecture:** 在 `server` 新增 GUI 本地配置服务与运行时配置解析层，扩展 `DraftConfig`/`RunSession`/`CourseRunSpec`，由 `RunService` 将全局默认值与课程覆盖解析成真实 CLI 参数；前端配置页新增 provider/base URL/model 配置区，运行页新增 hosted backend 摘要与 clean 状态说明。

**Tech Stack:** FastAPI, Pydantic, Next.js, TypeScript, local JSON config file, existing `processagent.cli`

---

## File Structure

- Create: `server/app/models/gui_runtime_config.py`
- Create: `server/app/adapters/gui_config_store.py`
- Modify: `server/app/main.py`
- Modify: `server/app/models/template_preset.py`
- Modify: `server/app/models/course_draft.py`
- Modify: `server/app/models/run_session.py`
- Modify: `server/app/application/course_drafts.py`
- Modify: `server/app/application/runs.py`
- Modify: `server/app/api/templates.py`
- Modify: `server/app/api/runs.py`
- Modify: `server/app/adapters/cli_runner.py`
- Modify: `server/tests/test_templates_api.py`
- Modify: `server/tests/test_runs_api.py`
- Modify: `web/lib/api/templates.ts`
- Modify: `web/lib/api/runs.ts`
- Modify: `web/components/config/template-config-workbench.tsx`
- Modify: `web/components/run/run-session-workbench.tsx`
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `PLANS.md`

## Task 1: Add GUI Runtime Config Models And Local Store

**Files:**
- Create: `server/app/models/gui_runtime_config.py`
- Create: `server/app/adapters/gui_config_store.py`
- Modify: `server/app/main.py`
- Test: `server/tests/test_templates_api.py`

- [ ] **Step 1: 写失败测试，覆盖 GUI 全局 provider/base_url/model 配置的读写约定**
- [ ] **Step 2: 运行 `python -m unittest server.tests.test_templates_api -v`，确认新测试先失败**
- [ ] **Step 3: 新增 GUI runtime config 模型，覆盖 provider、api key、base_url、simple_model、complex_model、timeout_seconds**
- [ ] **Step 4: 新增本地 JSON store，默认落到仓库外用户目录，并支持读取默认空配置**
- [ ] **Step 5: 在 `create_app()` 中注入 GUI config store/service，避免各 API 自己推导路径**
- [ ] **Step 6: 明确 API key 只通过单次 subprocess run 注入环境，不修改服务进程全局环境**
- [ ] **Step 7: 运行 `python -m unittest server.tests.test_templates_api -v`，确认通过**

## Task 2: Extend Draft Config For Provider And Model Routing

**Files:**
- Modify: `server/app/models/template_preset.py`
- Modify: `server/app/models/course_draft.py`
- Modify: `server/app/application/course_drafts.py`
- Modify: `server/app/api/templates.py`
- Modify: `server/tests/test_templates_api.py`

- [ ] **Step 1: 写失败测试，覆盖课程配置保存 provider/base_url/simple_model/complex_model 及回读行为**
- [ ] **Step 2: 运行 `python -m unittest server.tests.test_templates_api -v`，确认测试先失败**
- [ ] **Step 3: 扩展 `DraftConfigRequest` 与 `DraftConfig`，加入课程级 runtime override 字段**
- [ ] **Step 4: 更新 `CourseDraftService.save_config()`，同时持久化模板配置和 runtime override**
- [ ] **Step 5: 保持“空值表示继承全局默认值”的产品语义，不在前端写死默认 provider**
- [ ] **Step 6: 运行 `python -m unittest server.tests.test_templates_api -v`，确认通过**

## Task 3: Resolve Hosted Backend Runtime Spec In RunService

**Files:**
- Modify: `server/app/models/run_session.py`
- Modify: `server/app/application/runs.py`
- Modify: `server/app/adapters/cli_runner.py`
- Modify: `server/tests/test_runs_api.py`

- [ ] **Step 1: 写失败测试，覆盖 `create_run`/`resume_run` 将全局默认值 + 课程覆盖解析成 runner spec**
- [ ] **Step 2: 写失败测试，覆盖 `clean_run` 返回 `cleaned` 而不是 `running`，且不携带 hosted backend flags**
- [ ] **Step 3: 运行 `python -m unittest server.tests.test_runs_api -v`，确认新增测试先失败**
- [ ] **Step 4: 扩展 `RunSession`，保存 provider/backend、base_url、simple_model、complex_model、hosted 标识，并确保 session 持久化后可恢复**
- [ ] **Step 5: 在 `RunService` 中实现 runtime config 解析：provider、per-run API key 环境注入、simple/complex 到 stage models 的映射**
- [ ] **Step 6: 在创建 run 前校验 hosted 配置：API key、`base_url` 规范化、timeout 边界**
- [ ] **Step 7: 明确 `resume` 冻结创建时解析出的 backend/model routing；切换配置时创建新 run**
- [ ] **Step 8: 扩展 `CourseRunSpec` 与 `LocalProcessRunner` 参数拼装，接入 `--base-url`、`--model` 和 stage-specific model flags**
- [ ] **Step 9: 修正 `clean` 状态机，确保 clean 完成后保持 `cleaned`，仅 `run-course`/`resume-course` 进入 `running`**
- [ ] **Step 10: 运行 `python -m unittest server.tests.test_runs_api -v`，确认通过**

## Task 4: Expose GUI Settings And Course Overrides In Config Page

**Files:**
- Modify: `web/lib/api/templates.ts`
- Modify: `web/components/config/template-config-workbench.tsx`
- Modify: `server/app/api/templates.py`
- Test: `npm run lint`

- [ ] **Step 1: 扩展前端 API 类型，加入 GUI defaults 与课程 override 字段**
- [ ] **Step 2: 在配置页新增“运行后端设置”区块，支持 provider、API key、base URL、simple model、complex model**
- [ ] **Step 3: 把全局默认值与课程覆盖区分开，课程空值显示为“继承全局”**
- [ ] **Step 4: 保存模板配置时同时保存 runtime override；保存全局设置时写入本地 GUI config**
- [ ] **Step 5: 显示 hosted backend 风险提示，明确 API key 目前为本地明文配置**
- [ ] **Step 6: 运行 `npm run lint`，确认通过**

## Task 5: Update Run Page Summary And Clean Semantics

**Files:**
- Modify: `web/lib/api/runs.ts`
- Modify: `web/components/run/run-session-workbench.tsx`
- Modify: `server/app/api/runs.py`
- Test: `npm run build`

- [ ] **Step 1: 更新运行页摘要，显示 provider/backend、hosted 标识、simple/complex model、review_mode、target_output**
- [ ] **Step 2: 对 `cleaned` 状态增加明确文案：已清理，等待下一次启动/继续运行**
- [ ] **Step 3: 避免把页面类型或旧状态误显示成“正在执行”**
- [ ] **Step 4: 在 clean 后的 UI 上只保留下一步操作，不暗示后台仍在运行**
- [ ] **Step 5: 运行 `npm run build`，确认通过**

## Task 6: Document And Verify Real Backend Baseline

**Files:**
- Modify: `docs/runbooks/gui-dev.md`
- Modify: `PLANS.md`

- [ ] **Step 1: 更新 GUI runbook，记录 GUI config 文件位置、provider 支持范围、simple/complex model routing 规则**
- [ ] **Step 2: 在 runbook 中明确第一版密钥为仓库外本地明文配置**
- [ ] **Step 3: 把新批次写入 `PLANS.md`，只保留索引、范围和验证入口**
- [ ] **Step 4: 运行 `python -m unittest discover -s tests -v`**
- [ ] **Step 5: 运行 `python -m unittest server.tests.test_health server.tests.test_templates_api server.tests.test_runs_api -v`**
- [ ] **Step 6: 运行 `npm run lint` 与 `npm run build`**
- [ ] **Step 7: 记录已知缺口：系统凭据管理器、per-stage 独立模型、队列化执行**
