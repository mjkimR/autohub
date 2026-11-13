---
id: UC-decide-sdd-proposal
title: Retired Hub-native proposal decisions
summary: "The former Hub-authored proposal acceptance/rejection and workflow decision publication path is retired. Operators can inspect retained owner evidence without reviving its authority."
area: sdd
primary_actor: Project operator
supporting_actors: []
status: deprecated
capabilities: [CAP-SDD-native-delivery, CAP-SDD-workflow-control]
---

# [UC-decide-sdd-proposal] Retired Hub-native proposal decisions

## 1. Goal

- **Goal**: inspect the retained outcome and understand that the former operation
  grants no live execution authority.
- **Scope**: retained history and retirement refusal.
- **Trigger**: an operator opens an old subject or calls its retired operation.
- **Preconditions**: the operator is authenticated.

## 2. Main Success Scenario

1. The operator opens the retained owner subject (`CAP-SDD-native-delivery`).
   Interface: `UX-sdd-decision-history`, `UX-sdd-run`, `UX-run-decisions`, `UX-run-page`.
2. Hub displays the stored identity/outcome as historical evidence (`CAP-SDD-native-delivery`).
   Interface: `UX-sdd-decision-history`, `UX-sdd-run`, `UX-run-decisions`, `UX-run-page`.
3. The operator follows the linked Run/PR or leaves the retired subject (`CAP-SDD-native-delivery`).
   Interface: `UX-sdd-decision-history`, `UX-sdd-run`, `UX-run-decisions`, `UX-run-page`.

## 3. Extensions

- **1a.** Retained evidence is absent or inaccessible: Hub reports that exact
  subject unavailable; the use case ends without selecting another owner.
  Interface: `UX-sdd-decision-history`, `UX-sdd-run`, `UX-run-decisions`, `UX-run-page`.
- **2a.** A caller requests the retired live operation: Hub refuses before fresh
  work or repository evaluation; the use case ends. Off screen: this is an API refusal, not an active control.

## 4. Postconditions

- **Success guarantee**: the operator can distinguish historical evidence from
  an actionable execution.
- **Minimal guarantee**: opening history or retrying an old operation cannot
  grant authority to a replacement Run or effect.

## 5. Acceptance Criteria (Given / When / Then)

Applicable rules: `CAP-SDD-native-delivery` retained history and retirement.

### RETIRED-01: Read exact history

- **Covers**: main success scenario, 1a.
- **Given** an exact retained subject ID.
- **When** it is read.
- **Then** Hub returns its stored evidence or its exact unavailable outcome without execution.

### RETIRED-02: Refuse live authority

- **Covers**: 2a.
- **Given** a request for Hub-authored proposal acceptance/rejection and workflow decision publication.
- **When** the retired boundary receives it.
- **Then** no repository evaluation or new work is performed.

Retained mutation tombstones return `SDD_EXECUTION_RETIRED`. Local batch Stop settles future admission only; it does not resume work or cancel a provider.
