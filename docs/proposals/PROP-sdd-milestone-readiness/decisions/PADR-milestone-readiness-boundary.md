---
id: PADR-milestone-readiness-boundary
title: Keep milestone readiness separate from execution
summary: "For milestone work selection, we pin a read-only Hub preview to a repository commit and reuse devkit eligibility, to preserve execution authority, accepting refresh before later admission."
proposal: PROP-sdd-milestone-readiness
# supersedes: [ADR-<slug>]   # an ADR this decision replaces, wholly or in part; name the replaced clauses in Decision Outcome
status: draft
created_at: 2026-11-05
---

# [PADR-milestone-readiness-boundary] Keep milestone readiness separate from execution

- **Status**: Draft
- **Date**: 2026-11-05

---

## 1. Context & Problem Statement

The repository viewer shows branch-specific milestone proposals. Native activity admission evaluates workflow policy independently. A displayed document or local selection supplies no execution authority. Operators need one review of eligible milestone work before a later sequential executor exists.

## 2. Decision Drivers

- Preserve repository reading and existing execution authority.
- Identify one immutable document basis and exact dependency anchors.
- Reuse devkit eligibility and runtime isolation.
- Expose bounded uncertainty without presenting partial work as ready.

## 3. Considered Options

1. Separate Hub preview panel with backend evaluation: keeps selection and evidence together while preserving the viewer boundary.
2. Dedicated Hub preview screen: gives more room but adds navigation and state restoration for bounded results.
3. Viewer-only readiness badges: reuse navigation but cannot provide authoritative runtime admission or Hub-owned selection without vendor changes.

## 4. Decision Outcome

Choose the separate Hub panel because it meets the observation goal with existing ownership.

- All document membership and prerequisites use one captured repository commit. → `CAP-SDD-native-delivery` milestone preview interface (MUST).
- Readiness delegates workflow evaluation to the server-selected isolated devkit runtime and shares the existing native admission evaluator. → `CAP-SDD-native-delivery` milestone preview evaluation (MUST).
- Preview and selection create no repository changes, activities, PRs, runs, decisions or execution queues. → `CAP-SDD-native-delivery` observational preview (MUST).
- Incomplete evidence disables selectable ordered results, and later admission evaluates again. → `CAP-SDD-native-delivery` incomplete preview handling (MUST).

The named capability sections are proposed restatement locations; Development settles their rule numbers and confirms the trace during reconciliation.

## 5. Consequences

The preview has bounded runtime cost and requires refresh when its basis changes. Run/PR observations remain separately timestamped rather than an atomic snapshot. Conservative dependency holds may require source-reference repair. A later sequential executor needs its own authority and durable coordination contract.

## 6. Confirmation

Development verifies MR-01 through MR-08 with admission parity, immutable-ref, dependency, limit and stale-response fixtures. Review checks the retained `CAP-SDD-native-delivery` clauses and vendor-free UI diff. Planning checks the proposal's documented scope; it does not establish implemented guarantees.
