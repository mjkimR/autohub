---
id: PLAN-ci-static-references
spec: SPEC-ci-static-references
---

# CI static reference validation plan

## 1. Constitution & Invariant Review

No product capability, use case, storage or architecture invariant changes. Contributor command behavior belongs in the development guides. No ADR or general rule is needed for this bounded regression guard.

## 2. Architecture Overview & Impact

A read-only Python script parses workflow YAML run steps using already-declared PyYAML and obtains recipe and alias names with just --dump. A thin just recipe calls it; the existing backend lint wrapper invokes that recipe. No dependencies change.

## 3. Component & Interface Design

`python scripts/check-ci-references.py [--root PATH]` returns 0 for valid supported references and 1 for findings or unreadable/invalid input. The default root is the script checkout. Diagnostics name workflow, job and step. The summary counts inspected and skipped commands.

Only simple direct commands are tokenized with shlex. Backslash continuations and quoting are supported. Direct just invocations use the root justfile recipe namespace; just options, variable assignments before a command, computed words, redirection and compound shell are skipped. Echo/printf and YAML fields outside run are not path assertions. Literal config arguments, including --flag=config/path, resolve from step working-directory, job defaults, workflow defaults or repository root in that order. Dynamic working-directory skips the affected step. This bounded scanner is not a shell interpreter.

## 5. Error Handling & Edge Cases

Missing names and paths accumulate actionable findings. Invalid YAML, malformed quoting and failed just introspection fail instead of silently passing. Unsupported dynamic/compound forms are visible skips. CI run commands and just recipes are never executed.

## 6. Verification & Test Plan

The permanent command regressions use controlled temporary justfiles and YAML, with a recipe side-effect sentinel proving introspection is nonexecuting. Tests cover missing/existing recipe, aliases, quoted/option config paths, working-directory precedence, continuations, comments/prose, dynamic/compound skips, invalid input and the backend lint hook. Run Red before creating the script, then the same focused tests Green, actual just check-ci-references, just lint, just check and document/CI rules. No PostgreSQL or deployed E2E coverage applies to read-only contributor tooling.

Medium effort requires independent code review. Self reconciliation is appropriate because only root contributor tooling and its own guides change; no package or product contract behavior changes. Compare both guide edits to the checker and enforcing command tests, recording a reconcile-check envelope.
