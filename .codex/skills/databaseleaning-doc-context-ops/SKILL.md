---
name: databaseleaning-doc-context-ops
description: Use when working on databaseleaning repository documentation governance, docs structure changes, AGENTS updates, or spec/plan placement rules that must follow the repo's local docs system instead of the generic global doc-context-ops layout.
---

# Databaseleaning Doc Context Ops

## Overview

Use this repo-local skill for documentation governance tasks in `databaseleaning`.

The goal is to preserve the repository's existing docs system while giving superpowers-generated documents a stable, explicit place to live.

## Source Of Truth

Read these files before editing documentation structure:

- `AGENTS.md`
- `docs/AGENTS.md`
- `docs/README.md`
- `docs/workstreams/doc-system.md`
- `docs/superpowers/README.md`
- `docs/superpowers/doc-context-ops-compatibility.md`

## Repo Model

- Formal project documentation lives under `docs/architecture/`, `docs/schemas/`, `docs/workstreams/`, `docs/decisions/`, and `docs/runbooks/`.
- Superpowers working artifacts live under `docs/superpowers/`.
- `PLANS.md` is only the execution-batch index and status ledger.
- Root `AGENTS.md` is the navigation and rule entrypoint.

## Required Rules

1. Do not introduce `context/`, `overview/`, `workflow/`, or `archive/` as a replacement for the existing `docs/` tree.
2. Do not bulk-inject YAML frontmatter into the current docs tree unless the project explicitly adopts that metadata model.
3. Keep architecture, schema, decision, runbook, and workstream docs in their current sections.
4. Put generated design/spec documents in `docs/superpowers/specs/`.
5. Put generated implementation plans in `docs/superpowers/plans/`.
6. Update `PLANS.md` only for batch index, scope, status, and validation references; do not turn it into a full plan document.
7. When a documentation rule changes, update the nearest `AGENTS.md` or the most specific docs file that governs that behavior.

## Safe Workflow

1. Identify whether the task changes formal docs, superpowers artifacts, or both.
2. Preserve the existing section taxonomy unless the user explicitly requests a structural redesign.
3. Prefer additive clarification over tree-wide reorganization.
4. If a new document type is needed, place it under `docs/superpowers/` first unless it is clearly a formal project rule or architecture document.
5. After edits, verify links and summarize any new documentation boundary introduced.

## When Not To Use

- Do not use this skill for runtime assets under `out/`.
- Do not use this skill for code-only changes that do not affect docs, AGENTS, plans, or repo documentation workflow.
