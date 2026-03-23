# Legacy Prompt Notice

这个文件保留为历史入口说明，不再作为主执行 prompt。

当前系统已经改为多阶段 prompt：

- `blueprint_builder.md`
- `curriculum_anchor.md`
- `gap_fill.md`
- `compose_pack.md`
- `review.md`
- `canonicalize.md`

如果需要修改运行时行为，优先更新对应 stage prompt 与 `docs/` 中的 runtime contract，而不是继续扩展单一总 prompt。
