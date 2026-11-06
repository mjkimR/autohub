---
id: PROP-work-plan-templates
title: Create fresh Work Plans from reusable templates
summary: "Save reusable Work Plan specifications, local dependencies and execution preferences, then create explicitly reviewed new registrations without copying execution history or authority."
status: reviewing
created_at: 2026-11-06
target_area: capabilities/work-plans/
priority: low
size: M
planning_effort: medium
dev_effort: high
boundaries:
  owns:
  - modules/hub/app/features/project_management/work_plans/
  - modules/hub/migrations/
  - modules/hub/tests/integration/features/project_management/work_plans/
  - modules/hub/tests/integration/migrations/
  - modules/hub-ui/src/lib/api/
  - modules/hub-ui/src/lib/features/project-management/work-plans/
  - docs/capabilities/work-plans/
  - docs/usecases/work-plans/
  - docs/ux/work-plans/
  - docs/steering/
  excludes:
  - docs/operations/
  - .github/
  - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-work-plan-templates] Create fresh Work Plans from reusable templates

## 1. Background & Hypothesis

`CAP-WORK-work-plan-execution` registers task batches with local Item dependencies and execution preferences. Repeating a similar batch requires composing that specification again. Its execution history, merge evidence and replacement relationships belong to a particular registration and cannot serve as a reusable definition.

Save reusable Work Plan definitions and create fresh explicitly reviewed registrations from them. The hypothesis is that repeated maintenance or feature routines can reuse their structure while each execution retains independent identities and authority.

Recommended delivery order: third, after `PROP-mcp-delivery-tools` and `PROP-decision-notifications`. These are product priorities, not required implementation dependencies. Medium size is provisional; Planning should keep the feature to reusable Work Plan definitions and fresh registration.

## 2. Technical Spike Findings

The existing `WorkPlanWrite` contains title, description, base branch, absolute schedule, Plan dependencies, group metadata and Items; it has no per-Plan catalog/effort settings. `WorkItemWrite` contains local key, specification, acceptance, local dependency keys and optional explicit branch attachment. `WorkPlanService.create` serializes registration under the Project lock and uses its registration digest/request identity; creating an active Plan can invoke immediate admission after commit. Item branch names derive from Item keys, so copying keys unchanged makes repeated use collide with retained remote branches.

These findings are source inspection, not test execution. Evidence: `modules/hub/app/features/project_management/work_plans/{schemas.py,services.py,usecases.py,execution.py}` and `modules/hub-ui/src/lib/features/project-management/work-plans/WorkPlanForm.svelte` at base `0010af5fa2ca053e9023f90689f2cdb37a6bbaf5`.

## 3. Proposed Design & Impact

### Compared options and recommendation

| Option | Benefit | Cost / consequence |
| --- | --- | --- |
| A: clone an existing Plan into an unsaved editor | Minimal persistence | No reusable definition independent of execution history or revisioned template lifecycle. |
| B: project-scoped revisioned definition plus explicit fresh registration (recommended) | Reusable specifications with bounded isolation and ordinary execution ownership | Additive persistence and a thin registration transaction wrapper. |
| C: global shared templates with parameter language and schedules | Broad reuse | Adds cross-project binding, substitution and execution policy outside this task. |

Choose B. No new execution controller or general policy is needed; the scoped lifecycle choices below remain proposal decisions rather than a PADR.

### Definition and lifecycle

A Work Plan template is project-owned reusable definition metadata, separate from a Work Plan. Store an opaque UUID, name (1–200), revision (positive integer), supported definition JSON, schema version and created/updated actor/time. Use soft deletion with revision change; hide deleted templates from normal listing while retaining rows for known registration receipts. Updates require expected revision and replace the complete validated definition; stale edits/delete return 409. List is project-scoped, paged (limit 1–100, offset nonnegative) with deterministic name/ID order. Unknown/deleted/inaccessible templates return 404 for ordinary reads; malformed or unknown fields return 422. Existing signed-in human authorization applies, and actor identity comes from the authenticated user, never the body. No MCP template tools are added.

Definition allowlist: default Plan title/description, candidate base branch, and up to 100 local Item slots with key, title, description, acceptance and local dependency keys under existing text/graph limits. Persist neither group classification nor absolute schedule nor external Plan dependency IDs. These remain empty in a fresh preview until explicitly selected there. Do not invent unsupported catalog/effort fields. Exclude `attach_branch`, source Plan state, remote branch/PR/Issue identities, Run/Item UUIDs, results, attempts, recovery/replacement records, saved decisions and credentials. Reject disallowed fields in authored definition input. Save-from-Plan is a distinct command carrying source Plan ID and expected revision: acquire Project then source Plan lock, read one coherent current specification/edges snapshot, extract the allowlist server-side and report omitted categories. Source Plan revision conflict is 409 and creates no template. Saving never requests Issue publication, admission, dispatch or external calls.

CRUD command receipt identity is project+operation+request UUID with normalized body digest and authenticated actor. Identical replay returns its recorded outcome and current template revision/deleted state before current-revision checks; changed payload/actor is 409. Create/update/delete receipts persist even after deletion so response loss cannot create duplicate definitions or reapply edits. Definition saving and its receipt commit or roll back together. A plain form cancel before submission sends nothing.

### Fresh preview, registration and replay

Using a template first reads its exact revision and content digest into an editable client preview. Allocate a registration request UUID before deriving fresh Item keys: use a bounded readable stem plus the full request UUID hex (e.g. stem length at most 27 + '-' + 32 hex digits, total at most 60). Map every local dependency to the generated key, and show those keys for explicit editing. Use the original slot-to-generated mapping to avoid confusing source and fresh identities. Remote branch collisions still fail under existing owner rules; no uniqueness promise replaces those guards. No original `attach_branch` is carried. A deliberate explicit attachment can be entered in the ordinary registration editor and is separately visible in confirmation; it never comes from the definition.

The preview defaults to `state: draft`, `group_key: null`, `scheduled_at: null`, external Plan dependencies empty, current project repository/connector binding and the template's base branch as a labeled candidate. The operator reviews and can edit the complete resulting `WorkPlanCreate` content. Explicitly choosing active creation displays that eligible work can start immediately and follows current Plan readiness/admission policy. Creating a draft is not execution approval.

A new project-scoped template registration operation accepts exact template ID/revision/digest, expected current repository/connector binding, request UUID and the complete reviewed `WorkPlanCreate` payload. Its request UUID equals the owner's registration request UUID. Acquire Project lock then template lock. Check the wrapper's receipt before template-current, binding or revision eligibility: exact same operation/template/payload/actor returns the retained original Plan link, recorded template snapshot and current Plan state even after template edit/delete or Plan completion. A used request belonging to ordinary registration without this matching wrapper receipt conflicts; never label it template-derived. On a fresh request require a nondeleted matching template revision/digest and current binding; revalidate the edited payload with ordinary owner schemas and parent graph checks. Under that transaction call the existing `WorkPlanService.create`, persist resulting Plan ID plus immutable source template definition/version/digest, reviewed payload digest, actor/request and original binding in the registration receipt, then commit together. The source template is provenance, not a restriction against explicitly edited preview content. After commit use the existing owner admission kick only for active state. No second scheduler or duplicate PR controller is introduced.

A response-lost registration keeps its original endpoint/request UUID/full payload in project-scoped browser session storage until acknowledged or definitively refused by the owner. Label that storage on confirmation because specifications can contain private task text. Retain across remount/reload; clear on explicit acknowledgement/dismissal or logout, never share across accounts/projects. Reads use an exact template registration request lookup and never retry a write implicitly. Authentication/access/transport failures do not prove original refusal; preserve the request. While unresolved, block competing template mutations/registrations in that local project context; permit read-only checks and explicit exact retry. A successful write followed by refresh failure stays recorded with refresh error. A definitive revision/binding refusal requires fresh review, regenerated confirmation and a new request UUID; no silent fresh-revision resubmission. Template registration provenance remains independently readable after template deletion or source Plan changes and is not reconstructed from the current template.

### Interfaces and ownership

Provisional base `/api/v1/projects/{project_id}/work-plan-templates`: GET/POST collection; GET/PUT/DELETE `/{template_id}` with typed expected revisions/request IDs for writes; POST `/from-plan`; POST `/{template_id}/registrations`; GET `/registrations/{request_id}`. Static routes precede dynamic UUID routes. All requests use strict schemas and existing authentication. Reads make no external calls. Additive tables hold templates, CRUD receipts and registration receipts; existing Plans get no synthetic provenance. Retain nullable historical source IDs as snapshots where a foreign key would block unrelated historical migration/retention; enforce live project ownership through typed owner transactions. Choose exact database constraints during Development and cover migration metadata roundtrips.

### Candidate acceptance and Development checks

- **TEMPLATE-01**: Given a terminal or draft source Plan, saving its exact revision extracts only the allowlist, reports omitted fields, and creates no Issue/Run/PR/admission. Stale source revision or receipt-write failure leaves no template/receipt.
- **TEMPLATE-02**: Given one template used twice, previews have fresh deterministic request-bound Item keys with correctly remapped local edges; no source execution/attachment/authority enters either payload. Invalid/cyclic/missing local dependencies and bounds fail validation.
- **TEMPLATE-03**: Given a reviewed preview, concurrent template edit/delete or project binding change before fresh registration refuses without a Plan. Identical registration replay after template edit/delete returns the original retained receipt and current Plan; changed actor/template/body under that request conflicts.
- **TEMPLATE-04**: Given explicitly reviewed draft/active creation, the existing owner determines readiness, parent graph, repository/branch and admission behavior. Failed registration persistence rolls back both the Plan and template receipt; response loss after commit recovers the exact same Plan without duplicate dispatch.
- **TEMPLATE-05**: Given a derived Plan, editing/deleting its template or changing the source Plan never mutates that Plan's specification, lifecycle or execution evidence. Historical provenance remains readable and ordinary registration remains compatible.
- **TEMPLATE-06**: Given save/update/delete or registration response loss, remount/reload retains original immutable intent; checks are read-only, exact retry is explicit, and 401/403/read failures retain uncertainty. Refreshed preview changes clear confirmation. Successful write plus failed refresh preserves acknowledgement.

Development runs focused owner/API/migration tests, PostgreSQL races for edit/delete versus registration, atomic persistence and replay, UI save/use/changed-confirmation/unknown-response tests, typed API generation, `just lint` and `just check` after initialization. Preserve existing registration and metadata-roundtrip regressions. Baseline is the same head with template use absent: ordinary registration's behavior remains unchanged; no timing/count improvement is claimed.

### Future write scope and parallel work

Primary future code stays in new `template_models.py`, `template_schemas.py`, `template_repo.py`, `template_service.py`, `template_usecase.py`, `template_api.py` under the existing Work Plan owner. Existing edits are limited to `work_plans/api.py` router inclusion, `work_plans/models.py` model discovery, `WorkPlansPanel.svelte` entry, and `WorkPlanForm.svelte` reviewed preview seed. Add dedicated `WorkPlanTemplates.svelte`/intent helper and source-mirrored tests; keep UI size limits. Add one migration after the then-landed head. Shared generated output is `modules/hub-ui/src/lib/api/generated/work-plan.d.ts`; it can be regenerated after sequential merges. Existing full Work Plan migration roundtrip may need exact newer-table downgrade/upgrade setup in `modules/hub/tests/integration/migrations/test_work_plan_migration.py`. No production dependency on MCP or notifications is required. Resolve the shared migration chain and generated output in integration order; do not claim parallel write independence for those files.

### Non-goals

- **Scope Excluded**: recurring schedules, automatic decomposition, global/cross-project template marketplace, parameter substitution language, native SDD/SDK templates, automatic recovery/replacement and copied execution authority.
- **Scope Excluded**: catalog/effort settings not supported by current Work Plan input, MCP template tools, Jules integration, deployed-service verification, monitoring and CI changes.

## 4. Lifecycle & Retirement Criteria

This medium-effort Planning turn recommends option B under Host-authorized routine choices. High Development effort remains appropriate for additive persistence, idempotency and execution admission. No user-only business question is required; project scope, draft default and existing owner reuse are conservative assumptions for direction review. `target-docs.md` carries the retained UI candidate and owning contract changes. No acceptance, handoff or implementation is recorded. Complete Planning after challenger and separately authorized UX review, present any retained UX findings at plan-accept, then use the ordinary accepted-proposal handoff.
