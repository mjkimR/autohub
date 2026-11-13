---
id: PLAN-frontend-workflow-setup
spec: SPEC-frontend-workflow-setup
summary: "Reuse all-module initialization and the existing npm lint chain to repair contributor setup and fixing behavior."
---

# [PLAN-frontend-workflow-setup] Frontend workflow repair

## 1. Constitution & Invariant Review

None. `ADR-sdd-development` continues to govern SDD, pinned tools and asset restoration. This repairs existing contributor commands without changing product architecture, approval policy or dependency identities.

## 2. Architecture Overview & Impact

Set `worktree.setup` to the existing `just init` recipe. It runs locked Python synchronization, locked asset restoration and frontend installation. Devkit's subsequent worktree asset restoration remains harmless and idempotent. Initializing every module is deliberate because repository completion requires backend and UI checks even for a backend-only task.

Keep `scripts/lint.sh` as the shared recipe implementation. Its fixing UI branch runs the existing npm `format` script, then the existing `lint` script with `-- --fix`. Npm appends that flag to the final ESLint command in the existing `prettier --check . && eslint .` chain. The check branch continues to invoke `lint` without arguments. Both remain fail-fast through the shell and devkit runner.

The existing developer guides own setup and command usage. No capability, use-case, architecture or ADR changes are needed because the behavior is limited to contributing to Auto Hub itself. No new package script or recipe is added.

## 6. Verification & Test Plan

The regression test at `modules/hub/tests/unit/scripts/test_frontend_workflow.py` executes the real configured setup, just recipes and shell composition with controlled external tool shims. Formatting and ESLint fixtures change only under fix mode. Tests include read-only input preservation, error propagation and module selection. Shims are command-wiring evidence rather than a live npm registry or worktree lifecycle check.

Record Red before source changes, then Green under identical fixtures. Run the focused tests with `PYTEST_WORKERS=0 just test modules/hub/tests/unit/scripts/test_frontend_workflow.py`. Run `just init`, verify `uv run devkit sync --check` remains clean, then run full `just lint`, `just check` and source/doc CI rules. Inspect tracked status after npm setup and lint; package locks and product sources may not change. Independent code review is required at medium effort. Developer-guide reconciliation can be self-verified because only repository contributor tooling and its own guidance change.
