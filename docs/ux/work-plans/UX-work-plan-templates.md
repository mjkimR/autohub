---
id: UX-work-plan-templates
title: Work Plan Templates
summary: "Manage project-owned reusable definitions and recover exact original template requests independently of derived Plan execution."
area: work-plans
element: panel
status: active
usecases:
  - UC-reuse-work-plan-templates
capabilities:
  - CAP-WORK-work-plan-execution
---

# [UX-work-plan-templates] Work Plan Templates

## 1. Purpose

- **Primary task**: manage project reusable Work Plan definitions.
- **Facts to commit**: project, template name/ID/revision, item count, source Plan ID/revision when extracting, exact included specification and omitted execution/binding categories.
- **Secondary items**: complete specification editor below selection; fresh execution choices live in `UX-work-plan-editor`; existing Plan history stays in `UX-work-plans`.

## 2. Content

One paged template list is primary. New template and Save as template open a subordinate definition editor. Each row offers Use template, Edit template and Delete template. The definition editor shows name, default title, candidate branch and validated JSON for the complete allowed definition. An omissions notice names attachment/run/PR/Issue/history/approval, schedule/group and external Plan dependencies. The loaded source selector shows Plan ID/revision. Before Delete, confirmation states that derived Plans and historical receipts remain unchanged. A pending-intent disclosure shows operation/request identity, recorded-versus-unknown status and session-storage disclosure; it persists across panel close/reopen/reload for the signed-in account/project.

## 3. States

- **loading**: retain entry/Close, show loading, mutations disabled.
- **empty**: offer New template or Save as template from a Plan; Close available.
- **populated**: use/edit/delete selected template or load another page; list stays subordinate while editing.
- **editing**: save definition or cancel; change source requires a new coherent source read and clears prior confirmation.
- **saving**: immutable request pending; competing template mutations disabled, Close retains intent.
- **conflict**: retain unsent content, display the retained source/editor revision and refusal, then Reload for review or cancel; no silent overwrite.
- **unavailable**: template/source absent or inaccessible; Refresh list or return to ordinary Plan creation.
- **uncertain**: Check original request, Retry same request and Close; no new mutation until original result is known. Closing/dismissing an unresolved operation does not release the guard. Logout/session loss clears local private payload and loses this local guarantee; do not imply restoration or server deduplication under a fresh UUID.
- **recorded-refresh-error**: keep acknowledged outcome/ID, offer read-only Refresh, never replace with failed-write label.
- **error**: keep source/form and show validation/refusal; supported correction requires explicit review/new intent only after definite owner refusal.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open Templates / Save as template | `UC-reuse-work-plan-templates` 1, `UC-reuse-work-plan-templates` 2 | populated, empty | loading, editing |  | `CAP-WORK-work-plan-execution` | Exact project/source and omission summary visible; no execution. |
| Save definition | `UC-reuse-work-plan-templates` 3 | editing | saving, populated |  | `CAP-WORK-work-plan-execution` | Saved template ID/revision or retained uncertainty. |
| Use template | `UC-reuse-work-plan-templates` 4 | populated | populated | `UX-work-plan-editor` | `CAP-WORK-work-plan-execution` | Fresh editable draft, remapped keys and source snapshot loaded. |
| Edit / Delete and confirm | `UC-reuse-work-plan-templates` 7 | populated | editing, saving |  | `CAP-WORK-work-plan-execution` | Revision-aware change; derived Plans unchanged. |
| Reload / correct / cancel stale form | `UC-reuse-work-plan-templates` 2a, `UC-reuse-work-plan-templates` 7a, `UC-reuse-work-plan-templates` 7c | conflict, error | editing, populated |  | `CAP-WORK-work-plan-execution` | Unsaved text retained; stale confirmation cleared. |
| Check / Retry same request | `UC-reuse-work-plan-templates` 3a, `UC-reuse-work-plan-templates` 7b | uncertain | uncertain, populated |  | `CAP-WORK-work-plan-execution` | Exact immutable original intent is retained or acknowledged using read-only CRUD receipt lookup or explicit same-request write retry. |
| Refresh unavailable/list | `UC-reuse-work-plan-templates` 4a | unavailable, error | loading |  | `CAP-WORK-work-plan-execution` | No replacement template silently selected. |
| Refresh acknowledged result | `UC-reuse-work-plan-templates` 3b, `UC-reuse-work-plan-templates` 7d | recorded-refresh-error | populated, recorded-refresh-error |  | `CAP-WORK-work-plan-execution` | Recorded template identity remains visible; read-only refresh repeats no write. |
| Open original Plan | `UC-reuse-work-plan-templates` 6, `UC-reuse-work-plan-templates` 6b, `UC-reuse-work-plan-templates` 6c | populated, recorded-refresh-error | populated | `UX-work-plans` | `CAP-WORK-work-plan-execution` | Primary activation clears lifecycle/group filters, closes Templates and focuses the exact original Plan; modified links retain the exact anchor. Unavailable retained work shows guidance without substituting another Plan. |
| Close / Cancel unsent editor | `UC-reuse-work-plan-templates` *a | loading, populated, editing, saving, conflict, unavailable, error, recorded-refresh-error, uncertain | populated | close |  | Work Plans context restored; unresolved intent retained. |
| Next / Previous page | global: browse project definitions without execution | populated | loading |  |  | Deterministic bounded page, selected context preserved. |

## 5. Evidence

Source: `WorkPlanTemplates.svelte`, `TemplateDefinitionEditor.svelte`, `TemplateOutcome.svelte` and `template-intent.svelte.ts` under `modules/hub-ui/src/lib/features/project-management/work-plans/`. Enforcing interaction tests are `WorkPlanTemplates.integration.test.ts` and `template-intent.integration.test.ts` in that directory. Execution evidence belongs to `SPEC-work-plan-templates`; no browser walkthrough or live provider verification is asserted.
