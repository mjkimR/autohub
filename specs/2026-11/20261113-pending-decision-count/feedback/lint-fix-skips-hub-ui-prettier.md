---
id: FB-lint-fix-skips-hub-ui-prettier
title: just lint fixes backend formatting but only checks hub-ui formatting
scope: repo
kind: friction
category: tool-error
target: scripts/lint.sh
origin: agent
severity: workaround
recurring: false
status: open
created_at: 2026-11-13
---

# [FB-lint-fix-skips-hub-ui-prettier] just lint fixes backend formatting but only checks hub-ui formatting

## 1. Friction / Question (friction, question)

- **Context**: Running `just lint` (the fixing variant; `just lint-check` is the read-only one) after editing a hub-ui
  TypeScript file.
- **Expectation**: `just lint` passes `--fix` to `scripts/lint.sh`, which applies `ruff format` and `ruff check --fix`
  to Python, so formatting issues in hub-ui would also be written.
- **Actual**: For hub-ui the script runs `npm run lint` (`prettier --check . && eslint .`), so a Prettier difference
  fails the recipe instead of being fixed; the fix needs a separate `npm run format` from the module directory.
- **Workaround (or Interpretation Chosen)**: Reformatted the one line by hand and reran `just lint`.
- **Suggestion**: In fix mode, run `npm run format` (and `eslint --fix` where safe) for hub-ui before `npm run lint`.

## Evidence

```text
[RUN: "npm --prefix modules/hub-ui run lint" outcome=failed exit=1]
[warn] src/lib/features/project-management/pipeline-runs/pending-decisions.svelte.ts
[warn] Code style issues found in the above file. Run Prettier with --write to fix.
scripts/lint.sh:28: ... npm --prefix "$(resolve_module_path hub-ui)" run lint
```
