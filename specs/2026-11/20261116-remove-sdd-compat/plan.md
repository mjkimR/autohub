---
id: PLAN-remove-sdd-compat
spec: SPEC-remove-sdd-compat
---

# Technical Plan: `SPEC-remove-sdd-compat`

## 1. Constitution & Invariant Review

`ADR-remove-native-sdd-compatibility` replaces the retirement/history clauses of
`ADR-repository-owned-sdd-execution`. Repository-owned execution and ordinary PR safety remain.
The user authorizes removing unused legacy storage; preserve migration revision identifiers.

## 2. Architecture Overview & Impact

AC-01: remove evaluator tombstones, batch and native-decision HTTP/MCP/UI, discovery kinds and origin links.
AC-02: retain a standalone activity claim model/repository and uncertain-publication recovery;
remove native version gates from PR execution and claim admission.
AC-03: remove bridge worker, retained flow links, retirement gates and bridge-only runtime branches.
AC-04: add a forward schema migration, update current capability/use-case/architecture/UX contracts;
keep completed specs and superseded ADRs as history.

## 4. Storage & State Management

Drop the activity claim member foreign key, native batch tables and SDK PR link table in dependency order.
Keep durable standalone claims and generic flow/run receipts. Make the obsolete retirement data
migration a no-op while retaining its revision in the Alembic graph.

## 5. Error Handling & Edge Cases

Removed routes use ordinary missing-route behavior. Unsupported worker targets use generic
binding errors. Claim reconciliation remains restricted to uncertain publication with no Run
and no live lease, with actor/request replay and checkpoint digest checks.

## 6. Verification & Test Plan

Run focused backend SDD, PR, origin/owed/discovery, flow and MCP tests; relevant frontend tests;
forward migration upgrade/schema verification; regenerate UI OpenAPI types. Complete `just lint`,
`just check`, `just test-ui`, `just docs-check` and `just check-ui-api`.
