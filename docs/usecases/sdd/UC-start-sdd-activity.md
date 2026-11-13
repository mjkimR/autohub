---
id: UC-start-sdd-activity
title: Start repository-owned SDD work
summary: "An operator requests Planning or Development intent, obtains a Draft activity PR and follows its ordinary PR Run without Hub evaluating repository readiness. Exact claim recovery preserves uncertain publication."
area: sdd
primary_actor: Project operator
supporting_actors: [GitHub, Repository agent]
status: active
capabilities: [CAP-SDD-native-delivery]
entrypoints:
  - modules/hub/app/features/project_management/sdd/activities.py
  - modules/hub/app/features/project_management/sdd/api.py
---

# [UC-start-sdd-activity] Start repository-owned SDD work

## 1. Goal

- **Goal**: Request one repository activity as a tracked PR Run without preparing
  its development environment inside Hub.
- **Scope**: explicit Planning/Development start; completion belongs to
  `UC-complete-sdd-workflow`.
- **Trigger**: the operator selects a unit and requests work.
- **Preconditions**: the operator is authenticated.

## 2. Main Success Scenario

1. The operator selects the unit, activity, base and optional effort/catalog
   (`CAP-SDD-native-delivery`). Interface: `UX-sdd-proposals`.
2. Hub validates its project connection, request and exclusive owner
   (`CAP-SDD-native-delivery`). Interface: `UX-sdd-proposals`.
3. Hub publishes the exact activity branch and Draft PR through GitHub
   (`CAP-SDD-native-delivery`). Interface: `UX-sdd-proposals`.
4. Hub enrolls the ordinary PR Run with descriptive activity intent
   (`CAP-SDD-native-delivery`). Interface: `UX-sdd-proposals`.
5. The operator opens the returned Run to follow its work
   (`CAP-SDD-native-delivery`). Interface: `UX-sdd-proposals`, `UX-run-page`.

## 3. Extensions

- **2a.** Project, connection, catalog or base is unavailable: Hub refuses before
  new publication; the operator corrects the configuration and restarts step 1.
  Interface: `UX-sdd-proposals`.
- **2b.** Another owner or uncertain legacy claim exists: Hub identifies the
  retained owner/evidence and refuses replacement; the operator inspects it and
  explicitly reconciles the exact retired reservation before restarting step 1.
  Interface: `UX-sdd-proposals`, `UX-sdd-claim-recovery`.
- **3a.** An unrelated activity branch exists: Hub refuses without overwriting
  it; the use case ends. Interface: `UX-sdd-proposals`.
- **3b.** Publication response is unknown: Hub retains the original request and
  candidate evidence; the operator checks/retries that exact request and resumes
  at step 3. Competing starts remain unavailable. Interface: `UX-sdd-proposals`.
- **4a.** Enrollment fails after publication: the PR remains retained; exact
  owned-request recovery resumes at step 4 after the problem is corrected.
  Interface: `UX-sdd-proposals`.

Proposal state, size, dependencies, devkit lock/receipt and repository setup do
not create a Hub admission extension. The working agent handles those concerns.

## 4. Postconditions

- **Success guarantee**: one tracked activity Run refers to the intended Draft PR.
- **Minimal guarantee**: an unrelated branch is never overwritten; an uncertain
  effect is not treated as absent, rolled back or authority for another start.

## 5. Acceptance Criteria (Given / When / Then)

Applicable rules: `CAP-SDD-native-delivery` optimistic dispatch, host admission,
Draft publication, exact recovery and legacy reservation.

### SDD-START-01: Dispatch without repository readiness

- **Covers**: main success scenario.
- **Given** an enabled connected project and a requested unit without devkit setup.
- **When** the operator starts either activity kind.
- **Then** Hub returns a Draft activity PR/Run without installing or evaluating repository tooling.

### SDD-START-02: Refuse unavailable host configuration

- **Covers**: 2a.
- **Given** a missing connection/catalog/base.
- **When** the operator starts work.
- **Then** no new activity publication is authorized.

### SDD-START-03: Preserve another owner

- **Covers**: 2b, 3a.
- **Given** an existing owner, uncertain retired claim or unrelated branch.
- **When** another start is requested.
- **Then** Hub refuses replacement and preserves the exact retained evidence.

### SDD-START-04: Recover the original publication

- **Covers**: 3b, 4a.
- **Given** publication or enrollment lost its response.
- **When** the identical request UUID/payload is retried.
- **Then** Hub reconciles the original artifacts instead of creating replacements.

## 6. Verification Boundary

Activity/API and claim tests are cited by `CAP-SDD-native-delivery`. Local fixture
results do not establish provider delivery or a live GitHub merge.
