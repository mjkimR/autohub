---
id: ADR-milestone-readiness-boundary
title: Keep milestone readiness separate from execution
summary: "For milestone work selection, we pin a read-only Hub preview to a repository commit and reuse devkit eligibility, to preserve execution authority, accepting refresh before later admission."
proposal: SPEC-sdd-milestone-readiness
status: accepted
created_at: 2026-11-05
---

# [ADR-milestone-readiness-boundary] Keep milestone readiness separate from execution

- **Status**: Accepted
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

- All document membership and prerequisites use one captured repository commit. → `CAP-SDD-native-delivery` rule 21 (MUST).
- Readiness delegates workflow evaluation to the server-selected isolated devkit runtime and shares the existing native admission evaluator. → `CAP-SDD-native-delivery` rules 8, 23–24 (MUST).
- Preview and selection create no repository changes, activities, PRs, runs, decisions or execution queues. → `CAP-SDD-native-delivery` rule 26 (MUST).
- Incomplete evidence disables selectable ordered results, and later admission evaluates again. → `CAP-SDD-native-delivery` rules 25, 28–29 (MUST).

The named capability rules restate the accepted boundary.

## 5. Consequences

The preview has bounded runtime cost and requires refresh when its basis changes. Run/PR observations remain separately timestamped rather than an atomic snapshot. Conservative dependency holds may require source-reference repair. A later sequential executor needs its own authority and durable coordination contract.

## 6. Confirmation

`CAP-SDD-native-delivery` rules 21–29 restate the preview boundary. The enforcing fixtures are `modules/hub/tests/unit/features/project_management/sdd/test_milestones.py`, the API and real isolated catalog/Git tests beside `test_milestone_api.py` and `test_milestone_cli.py`, and the repository UI preview/selection suites. The spec's verification record separates executed checks from source inspection. Review verifies admission parity, exact snapshot/dependency handling, incomplete-result selection refusal and the vendor-free UI diff. No live deployment claim follows from these checks.
