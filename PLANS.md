# Plans

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
