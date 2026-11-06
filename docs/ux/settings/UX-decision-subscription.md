---
id: UX-decision-subscription
title: Decision notice settings
summary: "Review channel-owned decision settings and transport evidence with explicit request recovery."
area: settings
element: modal
status: active
usecases:
  - UC-configure-operator-notifications
capabilities:
  - CAP-NOTIFY-operator-notifications
---

# [UX-decision-subscription] Decision notice settings

## 1. Purpose

Save which observed decisions this trusted channel may disclose and when. Facts to commit: destination/chat and origin, project scope including future-project meaning, kind filters, effective channel gates, delivery mode and in-flight limit. Delivery history belongs in its sibling dialog.

## 2. Content

The settings form is primary above its disclosure and Save/Cancel controls.

- Notification channel: read-only name/chat, enabled flag and minimum severity.
- Decision subscription: enabled toggle (initial off); selected project IDs input or explicit All current and future projects; six decision-kind choices; immediate or 15-minute digest; adjacent helper explains Immediate becomes eligible on the next shared-maintenance pass, digest after15minutes on a subsequent pass, and neither guarantees a delivery deadline; Hub origin field and constructed example link.
- Effective outcome: current disabled/severity blocker, observed-not-live wording, existing matching pending decisions become eligible on enable/filter expansion, a 10-entry/3,500-character batch cap and the same next-maintenance/no-deadline timing summary before Save.
- Trust confirmation when enabling or changing destination/scope: The chat is trusted for selected project names, run/PR identities and decision metadata. Participants still need Hub sign-in to review. No question/answer content is sent.
- Future-admission disclosure: stopping or changing notices cannot recall an admitted external message.
- Save status: saved revision/time and reviewed destination generation; unknown save request ID and Check save outcome / Retry same save when applicable.

## 3. States

- **loading**: wait for settings, Cancel remains available; Save disabled.
- **populated**: edit settings, review disclosure, Save or Cancel.
- **saving**: lock mutation controls for this request; retain immutable UUID/payload until acknowledgement.
- **conflict**: retain edits and show changed revision; Refresh for review clears confirmation before fresh save.
- **unknown**: retain original request and disable changed-input save; Check save outcome or Retry same save; Close preserves unresolved intent in the active settings session. A full reload cannot claim recovery of an unacknowledged local payload; read saved settings before a new reviewed command.
- **error**: validation refusal identifies correction without implying transport delivery; Cancel or correct/review/save.
- **saved-refresh-error**: acknowledged save stays visible with Refresh failed; no replacement save is substituted.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Change project/kind/destination scope | `UC-configure-operator-notifications` 5 | populated | populated | | `CAP-NOTIFY-operator-notifications` | Effective summary updates; prior trust confirmation clears. |
| Save reviewed subscription | `UC-configure-operator-notifications` 6 | populated | saving | `UX-notifications` | `CAP-NOTIFY-operator-notifications` | Acknowledged settings and revision appear; failure retains form. |
| Refresh for review | `UC-configure-operator-notifications` 6a | conflict | populated | | `CAP-NOTIFY-operator-notifications` | Shows current settings plus destination generation and clears old confirmation. |
| Check save outcome / Retry same save | `UC-configure-operator-notifications` 6b | unknown | unknown, populated | | `CAP-NOTIFY-operator-notifications` | Reads exact actor-bound original request evidence separately from current settings, or replays the original command; absent receipt stays unknown. |
| Review changed destination | `UC-configure-operator-notifications` 6c | populated | populated | | `CAP-NOTIFY-operator-notifications` | Reveals current chat/origin/generation and requires fresh trust confirmation; an old generation is refused even from default subscription revision0. |
| Cancel or close | global: return without another save | populated, unknown, error | populated | close | | Parent remains; unresolved session intent is retained. |
