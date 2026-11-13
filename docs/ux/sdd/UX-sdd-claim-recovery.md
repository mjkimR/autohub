---
id: UX-sdd-claim-recovery
title: Retained activity ownership
summary: "Inspect a conflicting activity claim and explicitly acknowledge inspected external work before releasing a retained reservation. The acknowledgment cannot resume the old Run or create replacement work."
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
- **Secondary items**: the acknowledgment is unavailable until claim inspection succeeds.

## 2. Content

- Native SDD activity (Retained activity owner heading and **Inspect retained owner**).
- SDD activity claim (unit/activity/ID and exact **Open retained Run**/**Inspect original PR** links).
- Retired reservation (external-work explanation, acknowledgment checkbox and **Release inspected reservation**).

The explanation states that release neither stops an external agent nor resumes
the old Run. An active optimistic owner offers inspection rather than release.
A settled owner offers **Review new activity**, which returns to intent review.

## 3. States

- **uninspected**: Inspect retained owner loads exact evidence.
- **loading**: competing inspection/release is disabled.
- **reconcilable**: a retired claim or eligible unleased uncertain no-Run publication requires acknowledgment of inspected external work.
- **active**: follow the owning Run; no retired-reservation release is offered.
- **settled**: review new activity intent; no execution starts automatically.
- **error**: show the exact read/refusal outcome and retry permitted inspection.
- **uncertain**: retain the original acknowledgment UUID/digest; only **Retry same acknowledgment** can resend it.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Inspect retained owner | `UC-start-sdd-activity` 2b | uninspected, error | loading | | `CAP-SDD-native-delivery` | Exact claim and available evidence links load. |
| Open retained Run / Inspect original PR | `UC-start-sdd-activity` 2b | reconcilable, active, settled | populated | `UX-run-page` | `CAP-SDD-native-delivery` | The exact owner opens. |
| Acknowledge / Release inspected reservation | `UC-start-sdd-activity` 2b | reconcilable | loading | | `CAP-SDD-native-delivery` | The selected reservation settles without resume or new work. |
| Retry same acknowledgment | `UC-start-sdd-activity` 2b | uncertain | loading | | `CAP-SDD-native-delivery` | The identical retained request is replayed. |
| Review new activity | `UC-start-sdd-activity` 2b | settled | populated | `UX-sdd-proposals` | `CAP-SDD-native-delivery` | Intent review returns; a new start remains explicit. |

## 5. Evidence

Source: `modules/hub-ui/src/lib/features/project-management/repositories/SddClaimRecovery.svelte`.
No rendered browser or live external-work verification is claimed.
