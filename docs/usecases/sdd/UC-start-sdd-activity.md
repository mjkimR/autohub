---
id: UC-start-sdd-activity
title: Start repository-owned SDD work
summary: "An operator registers explicit repository-owned Planning or Development intent and receives its durable PR Run with a bounded first progression attempt."
area: sdd
primary_actor: Project operator
supporting_actors: [GitHub, Repository agent]
status: active
capabilities: [CAP-SDD-native-delivery]
entrypoints:
  - modules/hub/app/features/project_management/sdd/activities.py
  - modules/hub/app/features/project_management/sdd/api.py
  - modules/hub-ui/src/lib/features/project-management/repositories/SddUnitActions.svelte
  - modules/hub/app/features/project_management/sdd/usecases.py
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

1. The operator reads a proposal and reviews its contextual unit, activity, base and optional effort/catalog
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
- **2b.** Another owner or uncertain publication claim exists: Hub identifies the
  retained owner/evidence and refuses replacement; the operator inspects it and
  explicitly reconciles the exact uncertain no-Run reservation before restarting step 1. When a PR run owns the
  activity, the operator follows that run and may dismiss the original request; the use case ends.
  Interface: `UX-sdd-proposals`, `UX-sdd-claim-recovery`.
- **3a.** An unrelated activity branch exists: Hub refuses without overwriting
  it and closes the request, so later starts stay available; the use case ends. Interface: `UX-sdd-proposals`.
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
Draft publication, exact recovery, uncertain reservation, closed refusal, retained owner request and run-owned
request dismissal.

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
- **Given** an existing owner, uncertain publication claim or unrelated branch.
- **When** another start is requested.
- **Then** Hub refuses replacement and preserves the exact retained evidence.

### SDD-START-04: Recover the original publication

- **Covers**: 3b, 4a.
- **Given** publication or enrollment lost its response.
- **When** the identical request UUID/payload is retried.
- **Then** Hub reconciles the original artifacts instead of creating replacements.

### SDD-START-05: Keep intent beside its document

- **Covers**: main success scenario steps 1–2 and 3b.
- **Given** a selected proposal and a reviewed activity base.
- **When** the operator starts work or changes the selected unit/branch.
- **Then** the submitted intent uses the reviewed unit/base; context changes reset the editable form while unresolved original-request recovery remains available.

### SDD-START-06: Close a refusal without a retained owner

- **Covers**: 2a, 3a.
- **Given** a start refused for project configuration or an existing activity branch, with no retained claim named.
- **When** the refusal reaches the operator.
- **Then** the refusal is shown beside Start with its cause, the request is closed, and a later start in the project is not blocked.

## 6. Verification Boundary

Activity/API and claim tests are cited by `CAP-SDD-native-delivery`. Local fixture
results do not establish provider delivery or a live GitHub merge.

### SDD-START-07: Attempt first dispatch promptly

- **Covers**: main success scenario.
- **Given** a successfully registered activity with a bound claim.
- **When** registration commits.
- **Then** Hub attempts ordinary progression for up to 10 seconds; a deferred attempt preserves the registered Run for ticks.
