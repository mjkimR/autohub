---
id: PLAN-ux-documentation
spec: SPEC-ux-documentation
---

# Technical Plan: `SPEC-ux-documentation` Document implemented UX and shared objects

## 1. Constitution & Invariant Review

No product behavior, architecture invariant or accepted decision changes. Use the
installed devkit UX format and retain English authored prose. Existing UI source
is the reference; citations identify inspected evidence rather than fresh browser
or provider verification.

## 2. Architecture Overview & Impact

Add one shared object register under steering and an index under `docs/ux/`.
Document meaningful screens, modals and panels by feature area. Link current use
case steps and extensions to those elements without changing goals or step keys.
Treat visual subcomponents as content regions unless a person perceives them as
a separate operating surface. Keep API-only flows separate from browser claims.

Parallel authors own disjoint feature directories and use cases. The coordinator
owns the register, cross-feature index, terminology reconciliation and final
validation. Independent review compares the retained documentation to source.

## 6. Verification & Test Plan

- AC-01: inspect glossary/register consistency and run steering rules.
- AC-02: compare the route/view/dialog inventory with the UX index and source.
- AC-03: run native UX link and coverage rules and inspect semantic step mapping.
- AC-04: run `just docs-check`, full native linter/hygiene checks, local Markdown
  links and `git diff --check`. Run required `just lint` and `just check`.
- Product tests are unchanged; documentation checks do not certify live usage.
