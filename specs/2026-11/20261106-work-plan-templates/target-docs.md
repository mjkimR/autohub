---
id: PROP-work-plan-templates-target
title: Living Spec targets for Work Plan templates
summary: "Draft template lifecycle, fresh-registration use case and project-local management/review screens."
status: draft
proposal: SPEC-work-plan-templates
created_at: 2026-11-06
targets:
  - file: docs/capabilities/work-plans/CAP-WORK-work-plan-execution.md
  - file: docs/usecases/work-plans/UC-reuse-work-plan-template.md
  - file: docs/usecases/work-plans/UC-execute-work-plan.md
  - file: docs/ux/work-plans/UX-work-plan-templates.md
  - file: docs/ux/work-plans/UX-work-plan-editor.md
  - file: docs/ux/work-plans/UX-work-plans.md
  - file: docs/steering/glossary.md
  - file: docs/steering/ux-objects.md
---

# [Blueprint] Work Plan templates

This is a Planning draft, not an implemented contract.

## 1. Capability changes

Extend `CAP-WORK-work-plan-execution` with project-owned revisioned reusable definitions, allowlisted extraction, authenticated/idempotent CRUD, soft-delete retention and atomic template registration provenance. State explicitly that save/edit/delete do not request execution and that ordinary owner readiness/admission/replay still applies. Cover TEMPLATE-01–06 from the proposal with source-mirrored API/UI/PostgreSQL tests. Preserve existing Plan outcomes, Item identity, branch refusal, group/schedule and replacement contracts.

Add the following distinct glossary/register row during reconciliation: Work Plan template, reusable project-scoped definition owned by `CAP-WORK-work-plan-execution`; excludes Work Plan execution, Schedule configuration and SDK release. Representations: template name/revision/item count, saved definition editor, immutable-source editable registration preview. Calls to action: Save definition, Edit template, Delete template, Use template, Review registration, Check original request, Retry same request.

## 2. Use case draft

Planned UC-reuse-work-plan-template, Operator, capability `CAP-WORK-work-plan-execution`:

1. Operator opens Templates from the project Work Plans panel (`UX-work-plans` to planned UX-work-plan-templates).
2. Operator authors a definition or selects Save as template on a loaded source Plan; the template panel shows exact source/revision and omissions (UX-work-plan-templates).
3. Operator saves the definition; the panel confirms template ID/revision without execution (UX-work-plan-templates).
4. Operator selects Use template; Hub loads its exact revision and seeds a fresh draft registration preview with generated keys and remapped edges (UX-work-plan-templates to `UX-work-plan-editor`).
5. Operator edits/reviews resulting specification, fresh keys, current binding, target branch, optional fresh schedule/group/Plan dependencies and chosen state; confirms registration only after reviewing the complete payload (`UX-work-plan-editor`).
6. Hub atomically registers one fresh Plan and retained template provenance, then displays the original receipt and current Plan state (`UX-work-plan-editor` to `UX-work-plans`). Only active creation requests existing admission.
7. Operator can inspect/edit/delete an existing template independently of derived Plans (UX-work-plan-templates).

Extensions:
- **2a/7a source/template changed**: show 409, retain unsent form, require explicit reload/review; no automatic overwrite (UX-work-plan-templates).
- **4a template missing/deleted/inaccessible**: explain unavailable, return to template list or create an ordinary Plan (UX-work-plan-templates).
- **5a invalid graph/keys/readiness**: show owner validation, keep the editable unsent preview (`UX-work-plan-editor`).
- **5b template/binding changed**: registration refusal clears confirmation; show original versus current basis, reload and explicitly review a new request (`UX-work-plan-editor`).
- **3a/6a/7b uncertain write**: retain immutable endpoint/request/payload across remount/reload in account/project-scoped browser session storage, block competing template writes, offer read-only Check original request and explicit Retry same request (UX-work-plan-templates, `UX-work-plan-editor`). Do not clear uncertainty from auth/access/read failures.
- **3b/6b/7d write acknowledged, refresh failed**: keep the recorded template identity for 3b/7d (UX-work-plan-templates planned panel) or Plan link for 6b (`UX-work-plan-editor`), with a separate read-only refresh action and refresh error.
- **6c known request after template deletion/change**: recover original receipt/snapshot and current Plan without creating another Plan (`UX-work-plan-editor`).
- **7c concurrent deletion/update**: exactly one revision wins; existing Plans and saved registration snapshots remain unchanged (UX-work-plan-templates).
- **\*a cancel before send**: return to parent with no write. Closing unresolved operation keeps its account/project session intent; reopening restores it. Explain retained private task text and provide a read-only route; do not offer discard-and-resubmit as an uncertainty bypass.

Success: one reusable definition can yield independently reviewed fresh Plans. Minimum guarantee: no copied execution authority/history and no duplicate Plan from an unresolved template registration. Add reciprocal references from `UC-execute-work-plan` to template creation, keeping its ordinary execution steps intact.

## 3. Screens

### UX-work-plan-templates (planned panel)

- **Primary task**: manage project reusable Work Plan definitions.
- **Facts to commit**: project, template name/ID/revision, item count, source Plan ID/revision when extracting, exact included specification and omitted execution/binding categories.
- **Secondary items**: complete specification editor below selection; fresh execution choices live in `UX-work-plan-editor`; existing Plan history stays in `UX-work-plans`.

Content: one paged template list is primary. New template and Save as template open a subordinate definition editor. Each row offers Use template, Edit template and Delete template. Editor shows name/default title/description, candidate target, local slot keys, specification/acceptance and local dependency editor. An omissions notice names attachment/run/PR/Issue/history/approval, schedule/group and external Plan dependencies. Before Delete, confirmation states that derived Plans and historical receipts remain unchanged. A pending-intent disclosure shows operation/request identity, recorded-versus-unknown status and session-storage disclosure; it persists across panel close/reopen/reload for the signed-in account/project.

States:
- **loading**: retain entry/Close, show loading, mutations disabled.
- **empty**: offer New template or Save as template from a Plan; Close available.
- **populated**: use/edit/delete selected template or load another page; list stays subordinate while editing.
- **editing**: save definition or cancel; change source requires a new coherent source read and clears prior confirmation.
- **saving**: immutable request pending; competing template mutations disabled, Close retains intent.
- **conflict**: retain unsent content, display expected/current revision, Reload for review or cancel; no silent overwrite.
- **unavailable**: template/source absent or inaccessible; Refresh list or return to ordinary Plan creation.
- **uncertain**: Check original request, Retry same request and Close; no new mutation until original result is known. Closing/dismissing an unresolved operation does not release the guard. Logout/session loss clears local private payload and loses this local guarantee; do not imply restoration or server deduplication under a fresh UUID.
- **recorded-refresh-error**: keep acknowledged outcome/ID, offer read-only Refresh, never replace with failed-write label.
- **error**: keep source/form and show validation/refusal; supported correction requires explicit review/new intent only after definite owner refusal.

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open Templates / Save as template | UC-reuse-work-plan-template 1, UC-reuse-work-plan-template 2 | populated, empty | loading, editing | | `CAP-WORK-work-plan-execution` | Exact project/source and omission summary visible; no execution. |
| Save definition | UC-reuse-work-plan-template 3 | editing | saving, populated | | `CAP-WORK-work-plan-execution` | Saved template ID/revision or retained uncertainty. |
| Use template | UC-reuse-work-plan-template 4 | populated | populated | `UX-work-plan-editor` | Fresh editable draft, remapped keys and source snapshot loaded. |
| Edit / Delete and confirm | UC-reuse-work-plan-template 7 | populated | editing, saving | | `CAP-WORK-work-plan-execution` | Revision-aware change; derived Plans unchanged. |
| Reload / correct / cancel stale form | UC-reuse-work-plan-template 2a, UC-reuse-work-plan-template 7a, UC-reuse-work-plan-template 7c | conflict, error | editing, populated | | `CAP-WORK-work-plan-execution` | Unsaved text retained; stale confirmation cleared. |
| Check / Retry same request | UC-reuse-work-plan-template 3a, UC-reuse-work-plan-template 7b | uncertain | uncertain, populated | | `CAP-WORK-work-plan-execution` | Exact immutable original intent is retained or acknowledged using read-only CRUD receipt lookup or explicit same-request write retry. |
| Refresh unavailable/list | UC-reuse-work-plan-template 4a | unavailable, error | loading | | `CAP-WORK-work-plan-execution` | No replacement template silently selected. |
| Refresh acknowledged result | UC-reuse-work-plan-template 3b, UC-reuse-work-plan-template 7d | recorded-refresh-error | populated, recorded-refresh-error | | `CAP-WORK-work-plan-execution` | Recorded template identity remains visible; read-only refresh repeats no write. |
| Close / Cancel unsent editor | UC-reuse-work-plan-template *a | loading, populated, editing, saving, conflict, unavailable, error, recorded-refresh-error, uncertain | populated | close | | Work Plans context restored; unresolved intent retained. |
| Next / Previous page | global: browse project definitions without execution | populated | loading | | | Deterministic bounded page, selected context preserved. |

### UX-work-plan-editor (existing panel extension)

- **Primary task**: review and register a fresh Plan from a selected template snapshot.
- **Facts to commit**: template ID/revision/digest, fresh request ID, current project repository/connector, candidate target, draft versus active state, complete reviewed Item keys/edges/specification and fresh optional schedule/group/Plan dependencies.
- **Secondary items**: template CRUD stays in UX-work-plan-templates; current derived Plan execution follows `UX-work-plans`.

Content: preserve the ordinary editor as the primary region. Add a source-template summary and fresh Item-key mapping above it. Omitted execution/history fields are disclosed, not copied. Default state is draft. A final Review registration disclosure shows the complete chosen execution state and current binding; active choice warns that eligible work can start immediately. Any payload/basis edit invalidates acknowledgement. Buttons say Save draft or Register active work according to chosen state. Session-storage notice explains that unresolved payload text remains in this account/project browser session until resolved, acknowledged or logout.

States: **editing** can review/cancel; **confirming** can confirm or return to editing; **submitting** disables competing template writes; **conflict** shows old/current basis and requires re-review; **uncertain** retains original request across reload and permits only read-only checks/exact retry/close; **recorded** links original Plan/current state; **recorded-refresh-error** keeps acknowledgement and offers Refresh; **unavailable** offers Return to Templates; **error** retains unsent inputs and owner validation detail. Ordinary editor loading/empty behavior remains unchanged.

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Review registration | UC-reuse-work-plan-template 5 | editing | confirming | | `CAP-WORK-work-plan-execution` | Complete payload, fresh keys, binding and state reviewed. |
| Edit input/basis | UC-reuse-work-plan-template 5 | confirming | editing | | `CAP-WORK-work-plan-execution` | Confirmation clears; original source snapshot is explicit. |
| Confirm Save draft / Register active work | UC-reuse-work-plan-template 6 | confirming | submitting, recorded | `UX-work-plans` | Retained receipt and current Plan link; active admission disclosure. |
| Correct invalid payload | UC-reuse-work-plan-template 5a | error | editing | | `CAP-WORK-work-plan-execution` | Owner error points to inputs; no automatic write. |
| Reload changed basis | UC-reuse-work-plan-template 5b | conflict | editing | | `CAP-WORK-work-plan-execution` | Current template/binding loaded for a new reviewed request. |
| Check original request / Retry same request | UC-reuse-work-plan-template 6a, UC-reuse-work-plan-template 6c | uncertain | uncertain, recorded | | `CAP-WORK-work-plan-execution` | Same original operation/payload; missing read remains unknown. |
| Refresh acknowledged result | UC-reuse-work-plan-template 6b | recorded-refresh-error | recorded, recorded-refresh-error | | `CAP-WORK-work-plan-execution` | Recorded outcome remains distinct from refresh status. |
| Back to Templates | UC-reuse-work-plan-template 4a | unavailable | populated | UX-work-plan-templates | No new execution or substituted source. |
| Cancel / Close | UC-reuse-work-plan-template *a | editing, confirming, uncertain | populated | close | | Return to parent; original unresolved intent survives. |

### Alternatives and retained choice

Compare an inline clone-only action with a separate project-local Templates panel and an embedded template summary in the existing editor. Choose the separate management panel plus existing editor: reusable-definition lifecycle stays distinct from execution confirmation while preserving one registration entry point. No visual geometry is prescribed. Evidence is the source editor/panel at the retained base; these are text drafts, not browser-verified screens.

## 4. Reconciliation targets

Create the planned use case and template panel document; update the existing capability, editor, Work Plans entry, reciprocal execution-use-case links and glossary/object register. Do not change source owners during Planning. Source-created IDs above are planned targets; contracts become current only after implemented Development and reconciliation.
