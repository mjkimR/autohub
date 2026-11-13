---
id: UC-resume-verified-pr
title: Retired built-in verified PR resume
summary: "The former built-in checkout verification and fresh existing-PR bridge resume path is retired. Operators can inspect retained owner evidence without reviving its authority."
area: sdk
primary_actor: SDK flow operator
supporting_actors: []
status: deprecated
capabilities: [CAP-SDK-existing-pr-bridge]
---

# [UC-resume-verified-pr] Retired built-in verified PR resume

## 1. Goal

- **Goal**: inspect the retained outcome and understand that the former operation
  grants no live execution authority.
- **Scope**: retained history and retirement refusal.
- **Trigger**: an operator opens an old subject or calls its retired operation.
- **Preconditions**: the operator is authenticated.

## 2. Main Success Scenario

1. The operator opens the retained owner subject (`CAP-SDK-existing-pr-bridge`).
   Off screen: the client inspects retained API evidence; no dedicated browser control exists.
2. Hub displays the stored identity/outcome as historical evidence (`CAP-SDK-existing-pr-bridge`).
   Off screen: the client inspects retained API evidence; no dedicated browser control exists.
3. The operator follows the linked Run/PR or leaves the retired subject (`CAP-SDK-existing-pr-bridge`).
   Off screen: the client inspects retained API evidence; no dedicated browser control exists.

## 3. Extensions

- **1a.** Retained evidence is absent or inaccessible: Hub reports that exact
  subject unavailable; the use case ends without selecting another owner.
  Off screen: the client inspects retained API evidence; no dedicated browser control exists.
- **2a.** A caller requests the retired live operation: Hub refuses before fresh
  work or repository evaluation; the use case ends. Off screen: this is an API refusal, not an active control.

## 4. Postconditions

- **Success guarantee**: the operator can distinguish historical evidence from
  an actionable execution.
- **Minimal guarantee**: opening history or retrying an old operation cannot
  grant authority to a replacement Run or effect.

## 5. Acceptance Criteria (Given / When / Then)

Applicable rules: `CAP-SDK-existing-pr-bridge` retained history and retirement.

### RETIRED-01: Read exact history

- **Covers**: main success scenario, 1a.
- **Given** an exact retained subject ID.
- **When** it is read.
- **Then** Hub returns its stored evidence or its exact unavailable outcome without execution.

### RETIRED-02: Refuse live authority

- **Covers**: 2a.
- **Given** a request for built-in checkout verification and fresh existing-PR bridge resume.
- **When** the retired boundary receives it.
- **Then** no repository evaluation or new work is performed.

Synchronous new bridge effects return `SDD_BRIDGE_RETIRED`; unreceipted async work settles terminally. A saved resume receipt permits observation of its existing PR owner only.
