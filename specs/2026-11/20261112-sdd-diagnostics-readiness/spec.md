---
id: SPEC-sdd-diagnostics-readiness
title: Expose SDD diagnostics and readiness context
summary: "Preserve safe devkit diagnostics and preview the initial workflow state before enrolling a PR."
status: completed
created: 2026-11-12
related_capabilities:
  - CAP-SDD-runtime-isolation
  - CAP-SDD-workflow-control
related_usecases:
  - UC-complete-sdd-workflow
workflow: sdd-spec-feature
---

# [SPEC-sdd-diagnostics-readiness] Expose SDD diagnostics and readiness context

## 1. Problem Statement & Motivation

An operator inspecting native execution sees receipt/revision warnings but cannot consistently see devkit policy notices or actionable failure classifications. Registration readiness also hides the workflow stage and existing waits, although the API already evaluates them. This makes setup recovery and the decision to register a PR harder than necessary.

## 2. User Stories

- **US-1**: As an operator, I want safe diagnostic classifications and recovery guidance in readiness and execution review so I can distinguish repository repair, runtime repair and a decision.
- **US-2**: As an operator, I want the inspected first stage and existing questions, holds and approval requirements before registration so I can anticipate the run's initial state (`UC-complete-sdd-workflow` step 1).

## 3. Non-Goals

1. **Scope Excluded**: Automatic retries, execution of diagnostic actions, new approval rules, runtime migration, canary expansion and CI trigger changes.
2. **Scope Excluded**: Raw repository stderr, arbitrary upstream messages/actions/paths and new endpoints for diagnostic commands.
3. **Scope Excluded**: Reinterpreting registration eligibility as integration authority or a promise that the run can advance immediately.

## 4. Acceptance Criteria

### [AC-01] Project known diagnostic notices

- **Given** a devkit JSON result contains a recognized notice such as a retired approval-key warning.
- **When** native evaluation succeeds.
- **Then** readiness and retained run evidence expose a bounded Hub-authored diagnostic with code, severity, responsibility category, message, action, retry classification and static target files.

### [AC-02] Preserve safe failure guidance

- **Given** evaluation fails with a recognized CLI error, or unrecognized diagnostic content includes arbitrary paths, text or commands.
- **When** readiness or run observation reports the result.
- **Then** recognized errors retain structured safe guidance; unknown content becomes a generic Hub-authored diagnostic without copying arbitrary code, message, action, target path or stderr.

### [AC-03] Keep diagnostics out of execution identity

- **Given** the effective policy and workflow are unchanged while notice content changes.
- **When** an admitted run is reevaluated.
- **Then** diagnostic notices alone do not change semantic policy identity or grant retry, publication, answer or approval authority.

### [AC-04] Preview initial execution context

- **Given** readiness succeeds for the selected project, unit and PR.
- **When** the operator inspects the registration panel.
- **Then** it shows registration eligibility, inspected head/version, current stage, existing questions/problems/holds and applicable approval requests/policy, distinguishing an existing wait from eligibility to register.

### [AC-05] Invalidate stale previews

- **Given** readiness has been inspected.
- **When** project, unit or PR changes, or an older asynchronous response arrives.
- **Then** the old preview cannot enable Start execution or replace the selected combination's context.

### [AC-06] Retain historical warning display

- **Given** a saved run contains legacy warnings without structured diagnostics.
- **When** its native execution panel opens.
- **Then** the warnings remain visible, while structured results show diagnostic category, guidance and retry classification without duplicate legacy rows for the same code.

## 5. Screens

### Execution registration preview — panel (`UX-sdd-execution`)

**Purpose**: Inspect the selected SDD unit and PR before registration (`UC-complete-sdd-workflow` step 1).

**Content**: Keep existing inputs and readiness/start controls primary. Place a read-only Execution preview below inspection feedback. Show eligibility separately from a current wait. Secondary details contain inspected commit/version, next stage, question/problem/request summaries, approval policy and diagnostic guidance. Approval policy alone never labels an active approval wait; the current request or gate supplies that wait. A missing stage states that no next stage was reported, or that the workflow is complete when the result says so. Use the existing SDD unit and Native SDD activity representations in the UX object register; extend their readiness/evidence representations without adding an action type.

**States**: populated offers Check readiness; loading disables competing controls; eligible offers Start execution with the preview; eligible-with-wait retains Start execution and also explains why advancement will wait; failed inspection shows safe diagnostics and offers another inspection; changed selection removes the old preview; registered offers the existing execution link.

| Trigger | Step | From | To | Target | Feedback |
| --- | --- | --- | --- | --- | --- |
| Check readiness | `UC-complete-sdd-workflow` 1 | populated | loading | | Eligibility and initial context or safe failure guidance appear. |
| Start execution | `UC-complete-sdd-workflow` 1 | eligible | registered | `UX-run-decisions` | Existing registration result and execution link appear. |
| Change selected unit or PR | `UC-complete-sdd-workflow` 1 | eligible | populated | | The previous preview and registration enablement are invalidated. |

### Native execution diagnostics — panel (`UX-sdd-run`)

**Purpose**: Explain an observed native execution setup or workflow failure (`UC-complete-sdd-workflow` 3 and 5c).

**Content**: Place structured diagnostic code/severity, responsibility category, static summary/action and retry guidance beside current stage feedback. Keep operator decision controls and current authority unchanged. Legacy warnings remain readable when no structured counterpart exists.

**States**: populated shows known diagnostics; empty adds no diagnostic noise; error retains safe generic guidance when the failure is unknown. Guidance remains read-only and invokes no action. Retry classification describes whether reinspection is appropriate after repair; it offers no Retry now control.

| Trigger | Step | From | To | Target | Feedback |
| --- | --- | --- | --- | --- | --- |
| Inspect execution | `UC-complete-sdd-workflow` 3 | populated | populated | | Safe diagnostic guidance appears alongside current workflow evidence. |
| Close review | `UC-complete-sdd-workflow` 3 | populated | populated | close | Existing execution review closes without applying guidance. |

## 6. Assumptions & Invariants

The user authorized the two improvements. Registration, decision fencing, holds, publication and PR-owner authority remain owned by `CAP-SDD-workflow-control`. The allowlist boundary of `CAP-SDD-runtime-isolation` remains unchanged. The UI uses the existing panel arrangement, so no competing screen architecture is introduced.
