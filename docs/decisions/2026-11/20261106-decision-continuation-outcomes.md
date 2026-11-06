---
id: ADR-decision-continuation-outcomes
title: Expose owner outcomes beside explicit continuation
summary: "For decision follow-through, we expose owner-backed outcomes beside explicit continuation, to preserve authority and retry identity, accepting a typed read-model extension."
proposal: SPEC-decision-continuation
status: accepted
created_at: 2026-11-05
---

# [ADR-decision-continuation-outcomes] Expose owner outcomes beside explicit continuation

- **Status**: Accepted
- **Date**: 2026-11-05

---

## 1. Context & Problem Statement

An operator can save an answer, prepare its application, publish a native decision, or record integration authority. Their durable records belong to different owners. Current broad history cannot reliably locate an ordinary resume receipt or a native receipt beyond the history cap after a lost response.

## 2. Decision Drivers

- Preserve save/application, publication/delivery and historical/current-authority distinctions.
- Recover one operation without repeating external effects or overriding a later stop.
- Reuse existing owner records and prerequisite review context.

## 3. Considered Options

- Existing broad views only: minimal change, but lacks reliable exact resume receipt recovery.
- Typed read-only owner outcome lookup and retained owner review: direct correlation without another ledger; requires API/UI work.
- Independent continuation ledger/controller: uniform states, but creates duplicate truth and synchronization risk.

## 4. Decision Outcome

- Use the typed read-only lookup over owner records because exact recovery and authority preservation outweigh its API cost. → `CAP-PR-operator-decisions` outcome read contract (MUST).
- Keep saved answers, prepared application, publication, delivery and current authority as separate facts. → `CAP-SDD-workflow-control` outcome disclosure (MUST).
- Preserve original owner submission identity during uncertainty and use existing owner replay/reconciliation guards. → `CAP-SDD-native-delivery` decision recovery (MUST).
- Reuse the accepted inbox inspection and subject selection foundation; revalidate it against the landed predecessor before Development.

## 5. Consequences

The interface can retain a selected result after its pending row disappears. A missing receipt remains unknown; the system cannot promise a definite failure before a durable boundary. In-memory unacknowledged intent is not recoverable automatically after browser reload. Development reconciles the exact endpoint/fields with the landed predecessor and adds owner/UI verification; no separate persistence migration is planned.

## 6. Confirmation

Review only during Planning. Development verifies proposal E1–E11 with exact-request API, owner concurrency/publication and UI recovery tests, and reconciles the restating capability sections before acceptance of implementation. No application checks or deployed behavior are claimed here.
