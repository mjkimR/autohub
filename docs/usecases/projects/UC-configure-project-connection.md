---
id: UC-configure-project-connection
title: Configure a GitHub project connection
summary: "An operator connects a GitHub repository through encrypted connector credentials and explicit verification policy. Hub saves a revisioned project configuration and reports the outcome of a read-only connection check."
area: projects
primary_actor: Operator
supporting_actors:
  - GitHub
status: active
capabilities:
  - CAP-PROJ-project-connections
entrypoints:
  - modules/hub/app/features/project_management/projects/api/v1.py
  - modules/hub/app/features/configuration/connectors/api/v1.py
---

# [UC-configure-project-connection] Configure a GitHub project connection

## 1. Goal

- **Goal**: configure one repository connection with an inspectable verification
  outcome, so Hub can use its saved policy for subsequent work.
- **Scope**: connector/project configuration and read-only GitHub checking.
- **Trigger**: the operator connects a repository to Hub.
- **Preconditions**: the operator has signed in and has the external GitHub
  credential and intended CI policy available.

## 2. Main Success Scenario

1. The operator registers or selects the GitHub connector whose credential Hub
   stores without exposing it (`CAP-PROJ-project-connections`).
   Interface: `UX-connectors`, `UX-connector-create`, `UX-connector-edit`, `UX-project-connections`.

2. The operator supplies the repository and verification/automation policy
   (`CAP-PROJ-project-connections`).
   Interface: `UX-project-connections`, `UX-project-settings`.

3. Hub validates and saves the project connection with its owned dispatch schedule
   (`CAP-PROJ-project-connections`).
   Interface: `UX-project-connections`, `UX-project-settings`.

4. The operator inspects the saved configuration and revision without receiving
   credential contents (`CAP-PROJ-project-connections`).
   Interface: `UX-project-connections`, `UX-projects`.

5. The operator requests a read-only check against a representative PR
   (`CAP-PROJ-project-connections`).
   Interface: `UX-project-connections`, `UX-connection-test-check`.

6. Hub records the outcome against that configuration revision and reports its
   readiness and GitHub identity (`CAP-PROJ-project-connections`).
   Interface: `UX-connection-test-check`.

## 3. Extensions

- **2a.** Existing project: the operator submits only the intended changes with
  the revision they loaded; resume at step 3.
  Interface: `UX-project-connections`, `UX-project-settings`.

- **3a.** Invalid connector or verification policy: Hub returns HTTP `422`
  without saving the rejected connection; the use case ends for correction.
  Interface: `UX-project-connections`, `UX-project-settings`.

- **3b.** Repository already connected: Hub returns HTTP `409` instead of creating
  a competing mapping; the use case ends.
  Interface: `UX-project-connections`, `UX-project-settings`.

- **3c.** Stale project edit: Hub returns HTTP `409`; the operator reloads the
  configuration and resumes at step 2.
  Interface: `UX-project-connections`, `UX-project-settings`.

- **6a.** External check does not pass: Hub returns check failures and
  `ready: false` without treating the saved connection as verified; the operator
  corrects the configuration or external setup and resumes at step 2 or 5.
  Interface: `UX-connection-test-check`.

- **6b.** Project changed during checking: Hub returns HTTP `409` rather than
  publishing evidence for the replaced revision; the operator reloads and resumes
  at step 5.
  Interface: `UX-connection-test-check`.

## 4. Postconditions

- **Success guarantee**: a normalized repository has one saved Hub mapping, a
  project-owned dispatcher and a check associated with the saved revision.
- **Minimal guarantee**: rejected configuration does not create a competing
  mapping; public configuration omits secrets; a stale check does not become
  evidence for a newer configuration. A failed check does not remove saved setup.

## 5. Acceptance Criteria (Given / When / Then)

Rules exercised: normalized uniqueness, connector and CI validation, secret
boundaries, project revisions, owned schedules and check publication from
`CAP-PROJ-project-connections`.

### Scenario: Save and check a repository connection

- **Covers**: main success scenario.
- **Given**: an enabled GitHub connector, an unconnected repository and passing
  repository/workflow/PR/identity responses.
- **When**: the operator creates and checks the connection.
- **Then**: the repository is normalized, one dispatcher exists, no response
  exposes credentials and the saved check reports readiness for its revision.

### Scenario: Preserve omitted configuration during an edit

- **Covers**: 2a.
- **Given**: a connected project and its current revision.
- **When**: the operator patches only its name.
- **Then**: the connection policy remains, the revision increments and any previous
  saved check is cleared.

### Scenario: Refuse an unusable connector or CI contract

- **Covers**: 3a.
- **Given**: a disabled/missing connector or an invalid required-job contract.
- **When**: the operator submits the project configuration.
- **Then**: Hub returns HTTP `422` without saving that rejected mapping.

### Scenario: Refuse a case-variant duplicate repository

- **Covers**: 3b.
- **Given**: a project already connected to `owner/app`.
- **When**: another project requests `OWNER/APP`.
- **Then**: Hub returns HTTP `409` and retains the existing mapping.

### Scenario: Refuse an obsolete edit

- **Covers**: 3c.
- **Given**: a project changed after the operator loaded it.
- **When**: they patch using the older revision.
- **Then**: Hub returns HTTP `409` without applying the stale edit.

### Scenario: Separate failed checking from request success

- **Covers**: 6a.
- **Given**: a saved connection whose workflow fails or lacks a required job.
- **When**: the operator checks the representative PR.
- **Then**: the response reports `ready: false` and the failed verification even
  though the check request itself returns HTTP `200`.

### Scenario: Reject check publication after a concurrent edit

- **Covers**: 6b.
- **Given**: a connection check in progress against revision N.
- **When**: the project changes before the report is saved.
- **Then**: the check returns HTTP `409` and does not become the newer project's
  saved evidence.

## 6. Evidence

Inspected checks:
`modules/hub/tests/integration/features/project_management/projects/test_projects_api.py`,
`modules/hub/tests/integration/features/project_management/projects/test_dispatch_schedules.py`,
`modules/hub/tests/integration/features/configuration/connectors/test_connectors_api.py`
and `modules/hub/tests/unit/features/configuration/connectors/test_crypto.py`.
Partial-merge checks also appear in
`modules/hub/tests/unit/features/project_management/projects/test_project_schemas.py`.
These scenarios describe source/test-inspected behavior. They do not record a
fresh test execution or live GitHub/provider verification.
