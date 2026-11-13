---
id: SPEC-ci-static-references
title: Validate static CI recipe and config references
summary: "Catch missing literal just recipes and config paths in CI run steps through local lint checks without interpreting dynamic shell expressions."
status: planned
created: 2026-11-13
related_capabilities: []
related_usecases: []
workflow: sdd-spec-bugfix
---

# [SPEC-ci-static-references] Validate static CI recipe and config references

## 1. Problem Statement & Motivation

`FB-ci-workflow-manifest-paths-unchecked` records a removed config manifest and retired just recipe that remained in CI after local checks passed. The stale workflow was repaired; the missing local prevention check remains.

## 2. Defect Characterization

- **Current behavior**: backend lint checks package pins, source and documents but never inspect workflow run-step recipe or config references.
- **Expected behavior and its basis**: the authorized contributor check fails when a directly named recipe or literal config path is absent, with a workflow/job/step diagnostic.
- **Behavior to preserve**: the current workflow passes without running CI commands; lint-check remains read-only and frontend-only selection remains unchanged.
- **Reproduction conditions**: controlled workflow fixtures name a nonexistent recipe or deleted config file. Before the fix the checker is absent and these command regressions fail.

## 3. Non-Goals

1. **Scope Excluded**: executing CI, changing workflow definitions, parsing arbitrary shell or validating computed references.
2. **Scope Excluded**: recipe argument schemas, external actions, network validation, product behavior, dependencies and general governance rules.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Static recipe references
- **Given** YAML run steps containing simple direct just invocations
- **When** the checker reads the root justfile through just introspection
- **Then** missing recipes fail with exit 1 and workflow/job/step context; existing recipes and aliases pass without executing a recipe.

### [AC-02] Literal config references
- **Given** simple run commands with literal config/ or ./config/ path arguments, including quoted and option-assigned arguments
- **When** the checker resolves the paths against the step, job or workflow literal working-directory
- **Then** a missing path fails with exit 1 and its workflow/job/step context; existing paths pass.

### [AC-03] Deliberate syntax boundary
- **Given** comments, display/prose commands, multiline commands, dynamic references or compound shell
- **When** the checker inspects run fields
- **Then** comments and prose do not create findings, backslash continuation remains one logical simple command, and unsupported dynamic/compound commands are skipped with a visible count rather than interpreted.

### [AC-04] Local lint integration and current repository
- **Given** the default lint-check and current repository workflows
- **When** backend lint invokes the thin check-ci-references recipe
- **Then** the check runs before backend source checks, propagates failure without modifying input, and the current workflows pass.

## Source feedback

- `FB-ci-workflow-manifest-paths-unchecked`: directly fix local detection for literal recipe and config path references. Dynamic shell and general workflow validation remain outside the accepted scope.
