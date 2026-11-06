---
id: UC-reuse-work-plan-templates
aliases: [UC-reuse-work-plan-template]
title: Reuse a Work Plan Template
summary: "An operator saves project-local definitions and explicitly reviews fresh independent Plan registrations with exact original-request recovery."
area: work-plans
primary_actor: Operator
supporting_actors: []
status: active
capabilities:
  - CAP-WORK-work-plan-execution
entrypoints:
  - modules/hub-ui/src/lib/features/project-management/work-plans/WorkPlanTemplates.svelte
  - modules/hub/app/features/project_management/work_plans/template_api.py
---

# [UC-reuse-work-plan-templates] Reuse a Work Plan Template

## 1. Goal

- **Goal**: reuse a batch specification while each resulting Plan keeps independent execution identity and authority.
- **Scope**: project-local reusable definitions and fresh Work Plan registration.
- **Trigger**: the operator wants to repeat a specification or retain one for reuse.
- **Preconditions**: the operator has identified the intended project. Access, source freshness, graph validity and current binding are checked by Hub.

## 2. Main Success Scenario

1. The operator opens project Templates (`CAP-WORK-work-plan-execution`, `UX-work-plans`, `UX-work-plan-templates`).
2. The operator authors a definition or selects an exact loaded source Plan and reviews its included specification and omissions (`CAP-WORK-work-plan-execution`, `UX-work-plan-templates`).
3. Hub saves the definition and displays its original identity without starting execution (`CAP-WORK-work-plan-execution`, `UX-work-plan-templates`).
4. The operator selects the template and Hub prepares a fresh editable draft registration (`CAP-WORK-work-plan-execution`, `UX-work-plan-templates`, `UX-work-plan-editor`).
5. The operator edits and explicitly confirms the complete fresh specification, current binding and chosen execution state (`CAP-WORK-work-plan-execution`, `UX-work-plan-editor`).
6. Hub registers the independent Plan and its original template provenance together, then shows the original receipt and current Plan observation (`CAP-WORK-work-plan-execution`, `UX-work-plan-editor`, `UX-work-plan-templates`, `UX-work-plans`).
7. The operator manages the reusable definition independently of derived Plan execution (`CAP-WORK-work-plan-execution`, `UX-work-plan-templates`).

## 3. Extensions

- **2a.** Source or template changed: Hub refuses with `TEMPLATE_SOURCE_CHANGED` or `TEMPLATE_REVISION_CHANGED`; unsent content remains for correction and explicit reload/review; resumes at step 2 (`UX-work-plan-templates`).
- **3a.** Definition save response is uncertain: preserve immutable original intent; Check original request is read-only and Retry same request repeats that intent; resumes at step 3 only when recorded (`UX-work-plan-templates`).
- **3b.** Definition was recorded but refresh failed: retain original identity and offer read-only refresh; the save goal is reached (`UX-work-plan-templates`).
- **4a.** Template is missing, deleted or inaccessible: show unavailable and return to the list or ordinary creation; this reuse ends (`UX-work-plan-templates`, `UX-work-plan-editor`).
- **5a.** Graph, keys or executable specification is invalid: ordinary owner validation refuses; retain editable content for correction; resumes at step 5 (`UX-work-plan-editor`).
- **5b.** Template or repository/connector binding changed: Hub refuses with `TEMPLATE_REVISION_CHANGED` or `TEMPLATE_BINDING_CHANGED`; disable stale submission, explicitly reload the current basis and review a new request; resumes at step 4 (`UX-work-plan-editor`).
- **6a.** Registration response is uncertain: preserve original endpoint, identity and complete payload; allow only exact retry and read-only checks for that operation; resumes at step 6 when recorded (`UX-work-plan-editor`).
- **6b.** Registration was recorded but current-state refresh failed: retain original template identity and Plan link separately from refresh failure; the registration goal is reached (`UX-work-plan-editor`, `UX-work-plan-templates`).
- **6c.** A known request is checked after template change/deletion: Hub returns the original snapshot/Plan and separately observed current state without creating another Plan; the registration goal is reached (`UX-work-plan-editor`, `UX-work-plan-templates`).
- **7a.** Edit uses a stale template revision: show revision refusal and retain form content for explicit current-template reload; resumes at step 7 (`UX-work-plan-templates`).
- **7b.** Edit/delete response is uncertain: preserve the original immutable operation and block competing template writes; resolve by read-only check or exact retry; resumes at step 7 when known (`UX-work-plan-templates`).
- **7c.** Edit/delete races registration: one lock-serialized revision order wins; stale fresh commands refuse and existing Plans/receipts remain unchanged; resumes at step 7 (`UX-work-plan-templates`).
- **7d.** Edit/delete was recorded but refresh failed: keep acknowledged identity/deletion result and offer read-only refresh; the lifecycle operation goal is reached (`UX-work-plan-templates`).
- **\*a.** Operator cancels or closes: unsent inputs create nothing; an unresolved operation retains its account/project session intent across close/reopen/reload. Logout/session loss clears private local text and requires the original durable owner identity for recovery; this interaction ends (`UX-work-plan-templates`, `UX-work-plan-editor`).

## 4. Postconditions

- **Success guarantee**: a reusable definition and independently reviewed derived Plans retain their original provenance; only explicit active creation requests ordinary owner admission.
- **Minimal guarantee**: no partial Plan/provenance write, copied execution history/authority or duplicate Plan from an exact unresolved request. Access/read failure does not prove refusal. Session loss ends the local intent guarantee.

## 5. Acceptance Criteria (Given / When / Then)

Rules: allowlisted definition extraction; independent revisioned lifecycle; fresh key/edge mapping; atomic ordinary-owner registration; exact actor/target/body replay; durable local uncertainty and known-result recovery (`CAP-WORK-work-plan-execution`).

### TEMPLATE-01: Save and reuse safely

- **Covers**: main success scenario.
- **Given**: a source Plan with local dependencies and execution history.
- **When**: the operator saves its definition and reviews two uses.
- **Then**: only allowed specification enters the template, both previews default draft with independent remapped keys, and resulting Plans retain independent provenance without copied execution history.

### TEMPLATE-02: Refuse stale source and lifecycle edits

- **Covers**: 2a, 7a.
- **Given**: a source or template changed after it was loaded.
- **When**: the operator saves using its obsolete revision.
- **Then**: no stale mutation is applied and unsent content remains for explicit reload/review.

### TEMPLATE-03: Recover uncertain writes

- **Covers**: 3a, 6a, 7b.
- **Given**: a template CRUD/registration response was lost.
- **When**: the panel closes, remounts or reloads and the operator checks or explicitly retries.
- **Then**: the original immutable account/project intent survives, competing writes stay blocked, read/access failure stays unknown, and exact replay returns one original result.

### TEMPLATE-04: Keep acknowledged outcomes

- **Covers**: 3b, 6b, 7d.
- **Given**: a write was recorded but its following refresh failed.
- **When**: the operator reopens the panel.
- **Then**: original identity and Plan link where applicable remain recorded separately from the refresh error.

### TEMPLATE-05: Explain unavailable templates

- **Covers**: 4a.
- **Given**: a selected template is deleted or inaccessible.
- **When**: the operator uses it.
- **Then**: the panel reports unavailable without selecting another definition or registering work.

### TEMPLATE-06: Correct invalid reviewed work

- **Covers**: 5a.
- **Given**: an edited preview has an invalid local graph or incomplete active work.
- **When**: registration is requested.
- **Then**: owner validation refuses without partial persistence and the operator can correct unsent content.

### TEMPLATE-07: Review changed basis afresh

- **Covers**: 5b.
- **Given**: template content or project binding changed after preview.
- **When**: registration is refused and the operator chooses Reload for review.
- **Then**: the old preview cannot be submitted; current basis, new request/keys and explicit confirmation are required.

### TEMPLATE-08: Retain original provenance

- **Covers**: 6c, 7c.
- **Given**: a registration races template edit/deletion or a known template is later deleted.
- **When**: the command/receipt is read or identically replayed.
- **Then**: lock order determines fresh eligibility, and original Plan/provenance remain inspectable independently of current definition state.

### TEMPLATE-09: Close without bypassing uncertainty

- **Covers**: \*a.
- **Given**: unsent content or an unresolved operation.
- **When**: the operator closes the panel or logs out.
- **Then**: unsent content creates nothing, close retains unresolved identity/guard, and logout clears only the disclosed local private recovery namespace.

## 6. Evidence boundary

Source and test ownership are listed by `CAP-WORK-work-plan-execution`. Actual local API, PostgreSQL, migration and UI check execution is retained by `SPEC-work-plan-templates`. No live provider or deployed-service verification is claimed.
