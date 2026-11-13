---
id: CAP-SDK-existing-pr-bridge
title: Retired built-in existing-PR bridge
summary: "The evaluator-coupled autohub.sdd and autohub.pr_delivery SDK bindings are retired. Legacy receipt-backed delivery can observe its existing PR owner; generic SDK task/flow execution and scoped PR APIs remain available."
area: sdk
status: deprecated
usecases:
  - UC-resume-verified-pr
entrypoints:
  - modules/hub/app/features/execution/flows/bridge.py
---

# [CAP-SDK-existing-pr-bridge] Retired built-in existing-PR bridge

## 1. Summary

The built-in `autohub.sdd:*` and `autohub.pr_delivery:*` bindings no longer
verify repository checkouts or resume PR work. `ADR-repository-owned-sdd-execution`
retires both namespaces together. `CAP-SDK-task-flow-execution` continues to own
generic SDK releases, tasks, flows, approval and worker execution.

## 2. Scope & Boundary

- **In-Scope**: deterministic refusal of new bridge effects, durable settlement
  of old unreceipted work and observe-only recovery of receipt-backed delivery.
- **Out-of-Scope**: repository implementation and verification belong to its
  owner/agent and GitHub Actions. Ordinary PR control belongs to
  `CAP-PR-pull-request-delivery`; generic SDK execution belongs to
  `CAP-SDK-task-flow-execution`.
- **Scope Excluded**: checkout configuration, runtime provisioning, devkit
  evaluation, new built-in bridge effects or a replacement bridge protocol.

## 3. Business Rules & Policies

1. **Admission retirement**: WHEN a new built-in bridge registration/start/control would create work, Hub MUST refuse it with `SDD_BRIDGE_RETIRED`. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py`.
2. **Durable settlement**: WHEN old bridge work without a saved PR-resume receipt reaches execution, Hub MUST settle it terminally rather than treating retirement as transient worker unavailability. Check: the bridge retirement suite.
3. **Receipt-backed observation**: WHEN a legacy delivery has a saved PR-resume receipt, Hub MUST limit its progression to observing the existing PR owner without repeating resume or repository evaluation. Check: `test_receipt_backed_delivery_only_observes_existing_owner` in the bridge suite.
4. **History preservation**: Hub MUST preserve completed flow results and retained bridge evidence. Check: completed-result and flow retirement regressions in the bridge suite.

## 4. Interfaces & Data Contracts

Synchronous boundaries that would admit fresh bridge effects use HTTP 410
`SDD_BRIDGE_RETIRED`. Outstanding unreceipted asynchronous attempts produce a
terminal failed result carrying that code. Undispatched steps retire before a
worker claims them. A saved receipt is not permission to repeat its original
resume effect.

Exact existing idempotent start/command replay may return retained history.
Cancel retains the old delivery tombstone and ordinary owner cancellation for
already-resumed delivery; it does not start bridge work. Receipt-backed observation
requires the exact delivery attempt and same PR owner's saved resume receipt.

Retained bindings, claims and receipts are historical data. The host does not
need `AUTOHUB_FLOW_DELIVERY_TARGETS` or an operator checkout for these retired
namespaces. Ordinary scoped PR APIs remain available independently; they do not
inherit former bridge approval or repository-readiness guarantees.

## 5. Verification Boundary

The flow registration, worker and bridge-retirement paths define the source
contract. Tests cited above are source pointers, not a live GitHub/provider or
deployment result. `UC-resume-verified-pr` records the retired operator path.
