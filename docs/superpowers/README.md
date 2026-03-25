# Superpowers Docs

本目录存放 superpowers skills 生成的辅助文档，而不是项目正式规则的唯一事实源。

## Purpose

- `specs/`: 设计稿、方案比较、约束澄清
- `plans/`: 详细实施计划
- 其他子目录仅在确有稳定需求时新增

## Boundaries

- 正式架构、schema、运行规则、操作流程仍以 `docs/architecture/`、`docs/schemas/`、`docs/decisions/`、`docs/runbooks/`、`docs/workstreams/` 为准。
- `PLANS.md` 负责批次索引与状态汇总；这里的 plan 文档负责展开具体步骤。
- 若某个 superpower skill 自带另一套文档树约定，优先将产物映射到本目录，而不是改造现有 `docs/` 主树。

## Compatibility Notes

- `writing-plans` 默认输出到 `docs/superpowers/plans/`，与本仓库兼容。
- `brainstorming` 生成的 spec 应落到 `docs/superpowers/specs/`。
- `doc-context-ops` 的 `context/overview/archive`、frontmatter、自动索引约定默认不直接应用到本仓库主文档树；如需引入，先在项目文档里单独定义适配方案。

## Current Active Artifacts

- GUI v1 设计稿：[`specs/2026-03-23-gui-web-product-design.md`](specs/2026-03-23-gui-web-product-design.md)
- GUI v1 实施计划：[`plans/2026-03-23-gui-web-product-implementation.md`](plans/2026-03-23-gui-web-product-implementation.md)
- `PLANS.md` 中对应批次当前已标记为 `completed`
