---
id: SPEC-frontend-workflow-setup
title: Prepare frontend worktrees and apply lint fixes
summary: "Initialize frontend dependencies in task worktrees and make fixing lint apply UI formatting while preserving read-only lint-check behavior."
status: in-progress
created: 2026-11-13
related_capabilities: []
related_usecases: []
workflow: sdd-spec-bugfix
---

# [SPEC-frontend-workflow-setup] Prepare frontend worktrees and apply lint fixes

## 1. Problem Statement & Motivation

Contributor checks cover the backend and frontend, but task worktree setup installs only Python packages. The fixing lint recipe repairs Python formatting while only checking frontend formatting. Both gaps force manual recovery before the required contributor checks can pass.

## 2. Defect Characterization

- **Current behavior**: configured worktree setup omits frontend dependencies. `scripts/lint.sh --fix hub-ui` invokes the read-only npm lint script, so a formatting error fails without repair.
- **Expected behavior and its basis**: the contributor guide requires initialization and `just lint`/`just check` before completion. The fixing recipe repairs supported UI formatting and ESLint fixes. `just lint-check` checks without changing files. The two linked source feedback records state these existing expectations.
- **Behavior to preserve**: module aliases, backend/SDK selection, pinned Node activation, locked Python setup and failure exit propagation remain intact. Product behavior and dependency identities stay unchanged.
- **Reproduction conditions**: execute the configured setup and actual just/shell/npm script composition against disposable fixture files with controlled tool shims. Missing frontend setup and unrepaired UI input must fail before source changes.

## 3. Non-Goals

1. **Scope Excluded**: product code, API generation, dependency/pin/lock changes, CI workflow validation and a new development policy or command entry point.
2. **Scope Excluded**: a deployed service check or creating a second Git worktree for verification.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Complete task worktree initialization
- **Given** a task checkout without frontend dependencies
- **When** the configured setup command runs with the repository recipes
- **Then** it initializes locked Python packages, restores locked devkit assets and installs frontend dependencies using the pinned Node activation path; a failed phase returns nonzero.

### [AC-02] Fix frontend formatting and lint
- **Given** frontend fixture input requiring both formatting and an available ESLint fix
- **When** `just lint hub-ui` runs
- **Then** it applies formatting before the npm lint chain, enables ESLint fixing and returns zero only when that chain succeeds.

### [AC-03] Preserve read-only checks
- **Given** malformed frontend fixture input
- **When** `just lint-check hub-ui` runs
- **Then** it returns nonzero without changing the input or invoking a fixing operation.

### [AC-04] Preserve selection and failure reporting
- **Given** module aliases and a failing frontend formatter or linter
- **When** the fixing or checking recipe runs
- **Then** UI aliases follow their existing selection, non-UI selections invoke no frontend tool, and each failed selected phase stops the recipe with a nonzero result.

## Source feedback

- `FB-worktree-setup-skips-frontend-install`: resolve the complete configured initialization gap.
- `FB-lint-fix-skips-hub-ui-prettier`: resolve fixing-mode UI formatting and retain the read-only path.
