---
id: UC-preview-sdd-milestone
title: Review eligible milestone work
summary: "A project operator inspects an immutable milestone snapshot and reviews an eligible local subset without starting activities or saving a queue."
area: sdd
primary_actor: Project operator
supporting_actors:
  - GitHub
  - Server-selected devkit runtime
status: active
capabilities:
  - CAP-SDD-native-delivery
  - CAP-DOC-repository-viewer
entrypoints:
  - modules/hub-ui/src/lib/features/project-management/repositories/SddMilestonePreview.svelte
  - modules/hub/app/features/project_management/sdd/api.py
---

# [UC-preview-sdd-milestone] Review eligible milestone work

## 1. Goal

- **Goal**: Understand exact milestone members and their prerequisites, then review an explicitly selected eligible subset before separate execution admission.
- **Scope**: Auto Hub repository milestone preview.
- **Trigger**: The operator wants to inspect work in a repository milestone.
- **Preconditions**: The operator is authenticated.

## 2. Main Success Scenario

1. The operator chooses the repository ref and milestone (`CAP-DOC-repository-viewer`, `CAP-SDD-native-delivery`). Interface: `UX-repository`, `UX-sdd-milestone-preview`.
2. Hub displays the captured snapshot basis and completeness (`CAP-SDD-native-delivery`). Interface: `UX-sdd-milestone-preview`.
3. The operator inspects exact member readiness, prerequisites and related activity evidence (`CAP-SDD-native-delivery`). Interface: `UX-sdd-milestone-preview`.
4. The operator selects an eligible subset and reviews its suggested order (`CAP-SDD-native-delivery`). Interface: `UX-sdd-milestone-preview`.
5. The operator ends inspection or refreshes the observation (`CAP-SDD-native-delivery`). Interface: `UX-sdd-milestone-preview`.

## 3. Extensions

- **1a.** Project/ref/path/milestone validation refuses: The panel displays the refusal; the use case ends without evaluation authority or artifacts. Interface: `UX-sdd-milestone-preview`.
- **2a.** Discovery/evaluation is incomplete or exceeds a bound: Hub displays observed coverage and reasons with selection disabled; the operator may inspect rows or retry at step 2. Interface: `UX-sdd-milestone-preview`.
- **2b.** No direct members are observed: Hub displays an empty state; the operator chooses another milestone at step 1 or ends inspection. Interface: `UX-sdd-milestone-preview`.
- **3a.** A member is held, unsupported, finished, unknown or already active: The row remains inspect-only with its available evidence; resumes at step 3. Interface: `UX-sdd-milestone-preview`.
- **4a.** Context changes before an earlier response completes: Hub discards the old result and subset; resumes at step 1 for the current context. Interface: `UX-sdd-milestone-preview`.

## 4. Postconditions

- **Success guarantee**: The operator reviews only the explicitly selected eligible direct members at the displayed snapshot.
- **Minimal guarantee**: Inspection changes no repository, activity, PR, run, decision or scheduler state. Incomplete evidence supplies no selectable order or execution authority.

## 5. Acceptance Criteria (Given / When / Then)

### PREVIEW-01: Review a local subset

- **Covers**: main success scenario.
- **Given**: A complete milestone observation with eligible members.
- **When**: The operator selects a subset.
- **Then**: Only that subset appears in deterministic order and no activity starts or queue is persisted.

### PREVIEW-02: Refuse invalid context

- **Covers**: 1a.
- **Given**: Invalid project, ref or milestone identity/path.
- **When**: Preview is requested.
- **Then**: The refusal appears without fabricated readiness or artifacts.

### PREVIEW-03: Disclose incomplete coverage

- **Covers**: 2a.
- **Given**: Missing/ambiguous graph evidence, failed pagination/runtime or an exceeded bound.
- **When**: Preview returns.
- **Then**: Coverage and reasons remain visible and selection/order are disabled.

### PREVIEW-04: Explain an empty milestone

- **Covers**: 2b.
- **Given**: No direct proposal members are observed.
- **When**: The result is displayed.
- **Then**: Another milestone or refresh is offered without claiming completed delivery.

### PREVIEW-05: Inspect a held or existing activity

- **Covers**: 3a.
- **Given**: Unfinished prerequisites, workflow holds, unsupported historical anchors or an owned existing PR.
- **When**: The operator inspects a row.
- **Then**: Exact available anchor/worker/PR/run evidence appears without selecting, starting or resuming that activity.

### PREVIEW-06: Discard stale context

- **Covers**: 4a.
- **Given**: A selected subset or pending preview for an earlier context.
- **When**: Project, ref, milestone or refresh changes.
- **Then**: Selection clears and a late obsolete response cannot restore it.

## 6. Source and Verification Boundary

`CAP-SDD-native-delivery` links the enforcing backend and UI checks. Real Git/catalog/isolation fixtures establish the captured document basis; provider calls are doubled. No live provider or deployment result is claimed.
