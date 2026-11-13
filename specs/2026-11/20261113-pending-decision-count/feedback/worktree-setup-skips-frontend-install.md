---
id: FB-worktree-setup-skips-frontend-install
title: Task worktree setup leaves hub-ui without node_modules
scope: repo
kind: friction
category: instruction-conflict
target: .devkit/config.toml worktree.setup
origin: agent
severity: workaround
recurring: false
status: resolved
created_at: 2026-11-13
---

# [FB-worktree-setup-skips-frontend-install] Task worktree setup leaves hub-ui without node_modules

## 1. Friction / Question (friction, question)

- **Context**: A spec Unit started with `devkit worktree start dev-<slug>` changed a backend API and needed
  `just gen-ui-api`, `just test-ui` and the hub-ui lint/check in the new worktree.
- **Expectation**: The worktree setup prepares the environment the repository's required checks use
  (AGENTS.md requires `just gen-ui-api` after API changes and `just lint`/`just check` before finishing).
- **Actual**: The configured setup runs only `uv sync --no-active --locked --all-packages`; `modules/hub-ui/node_modules`
  is absent, so `just gen-ui-api` failed with an npm 404 while resolving its codegen tool.
- **Workaround (or Interpretation Chosen)**: Ran `just init hub-ui` in the worktree, then the frontend recipes passed.
- **Suggestion**: Make `worktree.setup` run `just init` (or add the hub-ui `npm install`), or state in the development
  guide that a new worktree needs `just init hub-ui` before frontend or typed-client commands.

## Evidence

```text
[WORKTREE_STARTED: ... setup="uv sync --no-active --locked --all-packages" synced=yes]
ls modules/hub-ui/node_modules -> No such file or directory
just gen-ui-api -> npm error 404 ... error: recipe `gen-ui-api` failed with exit code 1
just init hub-ui; just gen-ui-api -> Generated 27 API contract files from domain tags.
```

## Disposition

Resolved by `SPEC-frontend-workflow-setup`. Configured worktree setup reuses `just init`, initializing locked Python packages, locked devkit assets and frontend dependencies. The configured-command regression and phase-failure cases pass; actual `just init` and subsequent `devkit sync --check` pass. Fresh native worktree creation was not run; pinned lifecycle inspection verifies setup precedes the subsequent asset sync without a held recursive lock.
