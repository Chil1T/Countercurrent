# `doc-context-ops` Compatibility Notes

本文档定义 `databaseleaning` 如何吸收 `doc-context-ops` 的能力，而不破坏现有文档系统。

## Current Repo Model

- 文档根目录是 `docs/`，不是 `context/`
- 分类按 `architecture/`、`schemas/`、`workstreams/`、`decisions/`、`runbooks/`、`superpowers/`
- root `AGENTS.md` 是索引入口
- `PLANS.md` 是执行批次索引

## Skill Model Differences

- `doc-context-ops` 假设存在 `context/overview/workflow/experiments/archive` 文档树
- skill 默认依赖 YAML frontmatter、`doc_id`、`as_of_date`、`updated_at` 和自动索引
- 本仓库当前更重视稳定导航、规则分层和 planner/executor 可读性，而不是全量机读元数据

## Safe Adaptation Rules

1. 不自动重命名或迁移 `docs/` 主树目录。
2. 不默认给全部现有文档批量注入 frontmatter。
3. 若使用该 skill，先探测 root `AGENTS.md`、`docs/README.md` 和现有分区，再进入兼容模式。
4. 兼容模式下仅允许：
   - 审计 `docs/` 索引是否缺失
   - 补充 `docs/superpowers/`、`PLANS.md` 与正式文档层的职责说明
   - 在新建的 superpowers 工作产物文档上使用元数据
5. 只有在项目显式新增独立 `context/` 域时，才允许启用该 skill 的原生目录策略。

## Proposed Skill Changes

- 将 `doc-context-ops` 从固定目录约定改为“优先适配现有文档系统”的模式。
- 在 skill 开头增加项目探测步骤：
  - 若发现现成 `docs/README.md` 和 ADR/runbook 结构，则禁止目录迁移。
  - 若发现 `docs/superpowers/`，则将 skill 生成的辅助产物约束在该子树。
- 将 frontmatter 视为可选能力，只在项目声明需要机器检索和时效治理时启用。

## Recommended Project Follow-up

- 如后续需要机读索引，可新增单独的 `docs/doc-system.md` 或配置文件来声明 frontmatter 范围。
- 若未来真的引入 `context/`，应先写 ADR，再迁移，不要直接通过 skill 隐式重组文档树。
