---
id: UX-catalog-sessions
title: Catalog provider sessions
summary: "Review the retained results of Provider sessions for one AI catalog."
area: agents
element: modal
status: active
usecases:
  - UC-run-agent-session
capabilities:
  - CAP-AGENT-provider-sessions
---

# [UX-catalog-sessions] Catalog provider sessions

## 1. Purpose

- **Primary task**: Review the retained results of Provider sessions for one AI catalog.
- **Facts to commit**: Session state, work type, repository, failure detail and available result or delivery links.
- **Secondary items**: External session/PR links open separately; Pipeline run opens the existing delivery surface.

## 2. Content

Session history is primary below the status filter.

- AI catalog (dialog identity).
- Provider session (history row): title without its reconciliation suffix, work type, provider state and creation/repository details.
  - Failure detail, when recorded.
  - Result disclosure, when a final summary exists.
  - External session and PR links, when present.
  - PR run link, when retained; an expired-history notice appears after retirement.
- Paging: 20 rows per request, visible range/count, Previous and Next.

## 3. States

- **populated**: The selected history page is visible; expand Result, follow a link or page through results.
- **empty**: No sessions or no matching filter result; change the filter or close.
- **loading**: Loading sessions text replaces the list; paging controls are disabled.
- **error**: A request failure shows a toast and returns an empty history page; close and reopen, or change the filter to retry. No separate inline error panel is implemented.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Change status filter or page | `UC-run-agent-session` 7 | populated | loading |  | `CAP-AGENT-provider-sessions` | The selected catalog history page and count replace the previous results. |
| Expand Result | `UC-run-agent-session` 7 | populated | populated |  | `CAP-AGENT-provider-sessions` | The stored final summary is disclosed in the same row. |
| Pipeline run | `UC-run-agent-session` 7 | populated | populated | `UX-pipeline-runs` | `CAP-AGENT-provider-sessions` | The linked PR run is selected. |
| Open session or Pull request | `UC-run-agent-session` 7 | populated | populated | end | `CAP-AGENT-provider-sessions` | The external provider or PR opens in a separate tab. |
| Close | global: return to the catalog after session inspection | populated | populated | `UX-ai-catalogs` |  | The catalog list remains visible. |

| Dismiss dialog | global: dismiss session inspection | populated | populated | close | | The catalog list remains visible. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/ai-catalogs/CatalogSessionsDialog.svelte`.
