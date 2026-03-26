# `docs` AGENTS

- root `AGENTS.md` 只做索引与高层约束，详细内容放 `docs/`。
- 文档命名优先稳定、可链接、可长期维护。
- 同一主题优先追加到既有文档，不重复造轮子。
- 运行时产物不要写进 `docs/`；这里只记录规则、架构、流程与决策。
- 遇到 GUI runtime config、backend routing、`timeout_seconds`、model routing 一类问题时，优先补到 `runbooks/gui-dev.md` 与 `runbooks/run-course.md`，不要只在 spec/plan 里解释。
- 涉及 `docs/` 重组、文档分层、spec/plan 落点和 superpowers 兼容性时，先读取 `.codex/skills/databaseleaning-doc-context-ops/SKILL.md`。
