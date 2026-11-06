---
id: ADR-decision-notice-delivery
title: Poll owner decisions for channel-scoped notices
summary: "For decision notices, we poll persisted owner discovery into channel-scoped delivery receipts, to keep notification failure outside decision transactions, accepting bounded observation delay and explicit uncertain-send recovery."
proposal: SPEC-decision-notifications
status: accepted
created_at: 2026-11-06
---

# [ADR-decision-notice-delivery] Poll owner decisions for channel-scoped notices

## 1. Context & Problem Statement

Decision owners already maintain a persisted discovery projection in their own transaction. Existing global notification channels are severity-filtered external destinations without a durable receipt for each decision generation. A Telegram acceptance and a local database commit cannot be made atomic. The feature must preserve owner authority while exposing delivery uncertainty.

## 2. Decision Drivers

- Decision mutation availability remains independent of notification delivery.
- Scope, settings and deduplication remain explicit per trusted channel.
- Lost external responses never prove that a message was not delivered.
- Exact authenticated owner review determines current action eligibility.

## 3. Considered Options

- Poll existing persisted discovery into notification-owned receipts: bounded work and narrow owner coupling, accepting observation delay and missed transient generations.
- Enqueue notices in every owner transaction: captures more transient changes, adding mutation-path coupling without solving transport atomicity.
- Add links to current stop notices: smaller change but cannot satisfy project/kind subscription, digest and per-generation evidence.

## 4. Decision Outcome

Choose polling with channel-owned generation and attempt receipts.

- Notifications read current persisted owner discovery and do not evaluate repositories or mutate owner decisions while collecting. → `CAP-NOTIFY-operator-notifications` proposed Decision notices rules (MUST).
- Explicit channel subscriptions compose project/kind filters with existing enabled/severity gates; recipients are trusted destinations, not authenticated Hub principals. → `CAP-NOTIFY-operator-notifications` proposed Decision notices rules (MUST).
- Per-channel destination-generation and exact subject/fingerprint evidence survives history compaction; unknown sends are never automatically resent. → `CAP-NOTIFY-operator-notifications` proposed Decision notices rules (MUST).
- Exact links grant no authority and reuse authenticated current owner review, including existing native inspection/CAS effects. → `CAP-NOTIFY-operator-notifications` proposed Decision notices rules (MUST).
- Shared maintenance rotates bounded notification work without blocking existing execution work. → `ARCH-06-execution` proposed Decision notification maintenance boundary (MUST).

## 5. Consequences

The feature does not promise live freshness, notification of every transient generation, exactly-once Telegram delivery or cancellation of an admitted message. Durable generation tombstones add channel-lifetime storage; a future bounded-retention change must preserve dedupe or explicitly change that contract. If observed maintenance latency later prevents useful delivery, reconsider owner-transaction enqueue through a separate proposal rather than silently adding hooks.

## 6. Confirmation

Enforcement: `modules/hub/tests/integration/features/notifications/test_decision_notices.py` covers disabled baseline, revision-zero destination protection, atomic admission, unknown/lease fencing, dedupe, immutable replay, message budget and filter restoration. PostgreSQL admission uses independent competing transactions. `modules/hub/tests/integration/migrations/test_decision_notices.py` covers frozen-schema upgrade/downgrade. Notification UI, inbox exact selection and login-return tests cover current resend basis, refusal correction and authenticated navigation. `CAP-NOTIFY-operator-notifications` section6 and `ARCH-06-execution` Decision notification maintenance boundary restate the retained clauses. Execution counts are recorded in the owning SPEC envelopes; these checks use controlled external responses and claim no live Telegram, OAuth or deployment evidence.
