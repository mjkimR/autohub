---
id: UC-execute-sdd-batch
title: Inspect retained native SDD batches
summary: "Inspect an exact retained native batch from its Repository address, including history outside the latest list. Missing subjects and delayed responses never substitute another owner or revive retired execution."
area: sdd
primary_actor: Project operator
supporting_actors: []
status: deprecated
capabilities: [CAP-SDD-native-delivery]
entrypoints:
  - modules/hub-ui/src/lib/features/project-management/repositories/SddBatch.svelte
  - modules/hub/app/features/project_management/sdd/api.py
---

# [UC-execute-sdd-batch] Inspect retained native SDD batches

## 1. Goal

- **Goal**: inspect the retained outcome and understand that the former operation
  grants no live execution authority.
- **Scope**: retained history and retirement refusal.
- **Trigger**: an operator opens an old subject or calls its retired operation.
- **Preconditions**: the operator is authenticated.

## 2. Main Success Scenario

1. The operator opens the retained owner subject, including an exact batch address from Attention or a Run (`CAP-SDD-native-delivery`).
   Interface: `UX-sdd-batch`, `UX-project-detail`, `UX-attention`, `UX-repository`.
2. Hub displays the exact stored identity/outcome as historical evidence, including batches outside the latest list (`CAP-SDD-native-delivery`).
   Interface: `UX-sdd-batch`, `UX-project-detail`, `UX-attention`.
3. The operator follows the linked Run/PR or leaves the retired subject (`CAP-SDD-native-delivery`).
   Interface: `UX-sdd-batch`, `UX-project-detail`, `UX-attention`.

## 3. Extensions

- **1a.** Retained evidence is absent or inaccessible: Hub reports that exact
  subject unavailable; the use case ends without selecting another owner.
  Interface: `UX-sdd-batch`, `UX-project-detail`, `UX-attention`.
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
- **Given** a request for graph-derived native batch creation, resume and sequential admission.
- **When** the retired boundary receives it.
- **Then** no repository evaluation or new work is performed.

### RETIRED-03: Restore an old batch address

- **Covers**: main success scenario steps 1–2.
- **Given** an addressed batch outside the latest fifty.
- **When** its Repository link opens.
- **Then** exact detail loads directly; later list loading occurs once and preserves selection without mutations.

### RETIRED-04: Keep current history and failure identity

- **Covers**: 1a.
- **Given** a failed addressed batch or a delayed response for an earlier project/batch.
- **When** another list or detail read completes.
- **Then** the requested subject and its error remain accurate; neither older history nor another batch substitutes for it.

Retained mutation tombstones return `SDD_EXECUTION_RETIRED`. Local batch Stop settles future admission only; it does not resume work or cancel a provider.
