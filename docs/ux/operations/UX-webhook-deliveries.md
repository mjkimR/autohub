---
id: UX-webhook-deliveries
title: Webhook deliveries screen
summary: "Inspect retained GitHub delivery routing, processing state and failure explanations without replaying payloads or starting work."
area: operations
element: screen
status: active
usecases: []
capabilities:
  - CAP-PR-webhook-advancement
---

# [UX-webhook-deliveries] Webhook deliveries screen

## 1. Purpose

- **Primary task**: diagnose a recorded Webhook delivery outcome.
- **Facts to commit**: event, received time, repository/PR identity, processing state, attempts and outcome explanation.
- **Secondary items**: noteworthy/status filters and paging select records; execution controls remain in the PR-run interface.

## 2. Content

The delivery table is primary at `/operations/webhooks`. Only triggers and problems is enabled initially, alongside an Any/Received/Retrying/Processed/Failed status selector.

- Webhook delivery (table row): received time, event, optional @auto-run/catalog badge, repository/PR identity and status badge.
- Webhook delivery (processing evidence): repeat-attempt count and an outcome text describing waiting, replay, enrollment/advancement or failure detail.
- Webhook delivery (scope notice): payloads are not retained and the displayed record-retention statement is separate from the PR run lifecycle.
- Webhook delivery (page controls): first/last shown, total count and Previous/Next.

## 3. States

- **loading**: an initially empty table shows Loading webhook deliveries; the current refresh is disabled. Existing rows remain visible during later requests.
- **populated**: inspect routing and outcome records or change filters.
- **empty**: No deliveries match or No deliveries received yet is shown according to the selected filters; change filters or refresh.
- **error**: a load failure is toasted; previously displayed rows/counts remain unchanged, and there is no separate persistent error panel. Refresh can retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh | global: inspect operational state without starting the underlying work | populated | loading |  | `CAP-PR-webhook-advancement` | The current page reloads; failure is a toast and leaves the prior records. |
| Change noteworthy/status filters or page | global: inspect operational state without starting the underlying work | populated | loading |  | `CAP-PR-webhook-advancement` | Filters load from the first page; paging displays another retained-record slice. |
| Navigate through the console | global: navigation between management surfaces | populated | populated | `UX-pipeline-runs` |  | The chosen delivery-management screen appears. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/operations/webhook-deliveries/WebhookDeliveriesView.svelte`. Inspected check: `modules/hub-ui/src/lib/features/operations/webhook-deliveries/WebhookDeliveriesView.integration.test.ts`.
