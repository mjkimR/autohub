---
id: PLAN-work-item-replacement
spec: SPEC-work-item-replacement
---
# Technical plan: `SPEC-work-item-replacement`

## 1. Architecture Overview & Impact

Extend the existing Work Plan owner with additive replacement link, edge acceptance, event and operation receipt records. Router delegates to a use case owning transactions; service/repository helpers never commit. Project serialization covers mutation, admission, recovery and controls. No provider call is required.

## 2. Component Breakdown & Interface Contracts

Strict request schemas bind original and replacement Plan revisions plus evidence revision. Acceptance binds both specification digests and merge snapshot. Link history fixes endpoint roles for life. Read responses include immutable operation result and current relation, edge decisions and consumption events. Original Plan owns the URL. Request digest includes operation, path, actor and normalized command; replay precedes current eligibility.

The scheduler's existing local-edge query gains only a validated accepted-evidence alternative. Admission records consumed acceptance IDs in the same transaction as preparing. Plan dependencies and all other fences remain unchanged. Editable endpoint specifications are guarded while links remain active. Existing confirmed Work Item merge evidence survives detailed Run retirement.

UI extracts a cohesive per-Item review surface with candidate identifiers, exact snapshots, reason, explicit confirmation, conflicts and immutable request retry. It renders both endpoint identities and edge consumption; it creates no PR action.

## 3. Verification & Test Plan

Run SQLite owner/regression tests, PostgreSQL barrier races and migration roundtrip, UI review/conflict/response-loss tests, API generation, `just lint` and `just check`. Compare the same dependency fixture before acceptance and after exact-edge acceptance: zero vs one eligible local edge; no timing claim. High independent code and reconciliation reviews verify accepted criteria. `PROP-work-item-replacement-target` owns the retained screen draft and five initial Living Spec targets.
