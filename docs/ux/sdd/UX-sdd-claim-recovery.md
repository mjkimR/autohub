---
id: UX-sdd-claim-recovery
title: Retained activity ownership
summary: "Inspect a conflicting activity claim and explicitly acknowledge inspected external work before releasing a retained reservation. The acknowledgment cannot resume a Run or create replacement work."
area: sdd
element: panel
status: active
usecases: [UC-start-sdd-activity]
capabilities: [CAP-SDD-native-delivery]
---

# [UX-sdd-claim-recovery] Retained activity ownership

## 1. Purpose

- **Primary task**: inspect the exact retained owner before releasing a retained reservation.
- **Facts to commit**: project/claim, unit/activity, available Run/PR and inspected external work.
- **Secondary items**: the acknowledgment is unavailable until the claim read succeeds; request and claim identifiers sit in a collapsed Request details disclosure.

## 2. Content

- SDD activity claim (one card headed "<Activity> for <unit>" plus its situation: "has a retained owner", "is owned by a PR run", "has an uncertain reservation", "is still being published" or "has a settled owner").
- SDD activity claim (exact **Open retained Run**/**Original PR** links and **Inspect again**).
- Uncertain publication reservation (external-work explanation, acknowledgment checkbox and **Release inspected reservation**).
- SDD activity claim (Request details disclosure: project, request and claim identifiers, catalog and effort).

The claim evidence loads when the card opens. Each situation offers one primary next step. While a publication lease is live, the card explains that the lease still owns the work and re-renders when the lease expires, so release or retry becomes available without a reload.

The explanation states that release neither stops an external agent nor resumes
a Run. An active optimistic owner offers inspection rather than release.
A settled owner offers **Review new activity**, which returns to intent review.

## 3. States

- **loading**: the claim evidence loads when the card opens; competing inspection/release is disabled.
- **publishing**: a live publication lease still owns the work; Inspect again after it ends, then Retry same request.
- **reconcilable**: an unleased uncertain no-Run publication requires acknowledgment of inspected external work.
- **active**: follow the owning Run; no reservation release is offered.
- **settled**: review new activity intent; no execution starts automatically.
- **error**: a plain sentence states what failed and that nothing was released, adding a specific server reason only; Inspect again retries the read.
- **uncertain**: retain the original acknowledgment UUID/digest; only **Retry same acknowledgment** can resend it.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Inspect again | `UC-start-sdd-activity` 2b | populated, publishing, error | loading | | `CAP-SDD-native-delivery` | The exact claim and its evidence links are read again. |
| Open retained Run / Original PR | `UC-start-sdd-activity` 2b | reconcilable, active, settled | populated | `UX-run-page` | `CAP-SDD-native-delivery` | The exact owner opens. |
| Acknowledge / Release inspected reservation | `UC-start-sdd-activity` 2b | reconcilable | loading | | `CAP-SDD-native-delivery` | The selected reservation settles without resume or new work. |
| Retry same acknowledgment | `UC-start-sdd-activity` 2b | uncertain | loading | | `CAP-SDD-native-delivery` | The identical retained request is replayed. |
| Review new activity | `UC-start-sdd-activity` 2b | settled | populated | `UX-sdd-proposals` | `CAP-SDD-native-delivery` | Intent review returns; a new start remains explicit. |

## 5. Evidence

Source: `modules/hub-ui/src/lib/features/project-management/repositories/SddClaimRecovery.svelte`; `SddClaimRecovery.integration.test.ts` covers automatic loading, lease expiry while the card is open, read errors and the single situation heading.
No rendered browser or live external-work verification is claimed.
