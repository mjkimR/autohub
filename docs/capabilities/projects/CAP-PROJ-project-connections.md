---
id: CAP-PROJ-project-connections
title: Project connections and connector credentials
summary: "Hub projects bind normalized GitHub repositories to connector references, verification and automation policy. Connector secrets remain encrypted and omitted from public configuration, while revisions fence project edits and owned dispatch schedules follow the connection."
area: projects
status: active
usecases:
  - UC-configure-project-connection
entrypoints:
  - modules/hub/app/features/project_management/projects/api/v1.py
  - modules/hub/app/features/configuration/connectors/api/v1.py
---

# [CAP-PROJ-project-connections] Project connections and connector credentials

## 1. Summary

A Hub project may exist before GitHub is connected. A connected project binds one
normalized repository to a GitHub connector and explicit CI/automation settings.
The project owns its dispatch schedule; connector objects own encrypted provider
credentials and expose only credential presence to callers.

## 2. Scope & Boundary

- **In-Scope**: project/connector configuration, repository mapping, validation,
  revisions, managed project dispatch schedules and read-only connection checks.
- **Out-of-Scope**: human and machine admission belongs to
  `CAP-ACCESS-authentication-authorization` and `CAP-MCP-tool-access`; active agent
  diagnostics belong to `CAP-CONN-connection-verification`; catalog admission
  belongs to `CAP-AGENT-catalog-admission`; PR progression belongs to
  `CAP-PR-pull-request-delivery`; dispatch execution belongs to
  `CAP-EXEC-scheduling-maintenance`. GitHub and the operator own external token
  validity and provider-side setup.

## 3. Business Rules & Policies

1. **Repository identity**: WHEN a GitHub connection is supplied, Hub MUST strip
   surrounding whitespace and lowercase its `owner/repository` identity.
   Checks: `modules/hub/tests/integration/features/project_management/projects/test_projects_api.py`,
   `modules/hub/tests/unit/features/project_management/projects/test_project_schemas.py`.
2. **Unique mapping**: IF another project already owns that normalized repository,
   THEN Hub MUST refuse the conflicting create or edit with HTTP `409`.
   Check: `modules/hub/tests/integration/features/project_management/projects/test_projects_api.py`.
3. **Connector suitability**: IF the selected GitHub connector is missing,
   disabled or not a GitHub provider, THEN Hub MUST refuse the connection with
   HTTP `422`.
   Check: `modules/hub/tests/integration/features/project_management/projects/test_projects_api.py`;
   provider branch inspected in `modules/hub/app/features/project_management/projects/services.py`.
4. **Verification validation**: IF the workflow or required-job specification
   violates its schema, THEN Hub MUST refuse project registration with HTTP `422`.
   Checks: `modules/hub/tests/integration/features/project_management/projects/test_projects_api.py`,
   `modules/hub/tests/unit/features/project_management/projects/test_project_schemas.py`.
5. **Secret storage**: WHEN connector credentials are written, Hub MUST encrypt
   them with AES-GCM bound to connector identity and provider.
   Checks: `modules/hub/tests/integration/features/configuration/connectors/test_create_connector.py`,
   `modules/hub/tests/unit/features/configuration/connectors/test_crypto.py`.
6. **Public configuration**: Connector reads and project responses MUST omit
   plaintext credentials and stored credential ciphertext.
   Checks: `modules/hub/tests/integration/features/configuration/connectors/test_connectors_api.py`,
   `modules/hub/tests/integration/features/project_management/projects/test_projects_api.py`.
7. **Revision fence**: IF a project patch's `expected_revision` differs from the
   loaded project revision, THEN Hub MUST refuse it with HTTP `409`.
   Check: `modules/hub/tests/integration/features/project_management/projects/test_projects_api.py`.
8. **Check invalidation**: WHEN a project edit succeeds, Hub MUST increment the
   revision and clear its prior saved connection check.
   Check: `modules/hub/tests/integration/features/project_management/projects/test_projects_api.py`.
9. **Owned dispatcher**: WHEN a project first gains a GitHub connection or a save
   finds its dispatcher missing, Hub MUST create its project-owned dispatcher.
   Check: `modules/hub/tests/integration/features/project_management/projects/test_dispatch_schedules.py`.
10. **Disconnect and reconnect**: WHEN an existing project disconnects GitHub,
    Hub MUST disable its owned dispatch schedule without deleting its history.
    Check: `modules/hub/tests/integration/features/project_management/projects/test_dispatch_schedules.py`.
11. **Schedule authority**: IF a generic schedule operation tries to create,
    duplicate, edit or delete a project-owned dispatcher, THEN Hub MUST refuse it
    with HTTP `409`.
    Check: `modules/hub/tests/integration/features/project_management/projects/test_dispatch_schedules.py`.
12. **Read-only check**: WHEN a connection check runs, Hub MUST restrict its
    GitHub requests to reads of repository, workflow, PR verification and identity.
    Check: `modules/hub/tests/integration/features/project_management/projects/test_projects_api.py`.
13. **Check publication fence**: IF the project revision changes while its
    connection check is running, THEN Hub MUST refuse publication with HTTP `409`.
    Check: `modules/hub/tests/integration/features/project_management/projects/test_projects_api.py`.

## 4. Interfaces & Data Contracts

All routes below have the `/api/v1` prefix. Protected REST operations require a
signed-in active user; project mutations through MCP instead require the
operations endpoint and scope defined by `CAP-MCP-tool-access`.

| Route | Contract |
| --- | --- |
| `POST /connectors` | `name`, provider `github` or `jules`, nonempty credential object, optional config/enabled; HTTP `201` |
| `GET /connectors`, `GET /connectors/{connector_id}` | Metadata and `has_credentials`, never secrets/ciphertext |
| `PATCH /connectors/{connector_id}` | Omitted fields preserve current values; supplied credentials replace the encrypted credential object |
| `PUT /connectors/{connector_id}` | Full connector replacement with a credential object |
| `POST /projects` | `name`, `project_type` (`general` or `sdd`), optional `github`, enabled; HTTP `201` |
| `GET /projects`, `GET /projects/{project_id}` | Current configuration, revision and saved check; project pages use limit 1–100 |
| `PATCH /projects/{project_id}` | Required `expected_revision`; nested objects merge, arrays/scalars replace; `github: null` disconnects |
| `POST /projects/{project_id}/check` | Positive `pull_number`; returns check items, `ready`, `project_revision`, optional observation and GitHub login |
| `POST /projects/import_schedule` | Atomically adopts legacy `pipeline.observe`; retains trigger, PR numbers and schedule history |
| `DELETE /projects/{project_id}` | HTTP `204` only after the service permits removal of the project's retained references |

`github` contains `repository`, `github_connector_id`, `verification`, optional
template/catalog selection and automation. Explicit catalog selection is validated
for PR-delivery capability; runtime admission remains the catalog's responsibility.
The dispatch interval defaults to 60 seconds and accepts 30–3600 seconds. A
disconnected project has no newly created dispatcher. Reconnection reuses an
existing dispatcher and retains `last_run_at`; the schedule's enabled state follows
both project enablement and connection presence.

The credential patch boundary is determined by fields actually supplied in the
request. Omitting `credentials` preserves existing ciphertext; supplying it
re-encrypts the replacement object with a fresh nonce. Source review:
`modules/hub/app/features/configuration/connectors/services.py`; the omission
branch has no dedicated assertion in the inspected API tests. Decryption also
requires an enabled connector of the expected provider and a nonempty string
`token`. Key configuration and rotation procedures belong in the
[connector operations guide](../../../modules/hub/README.md#connector-credential-encryption).

A check can return HTTP `200` with `ready: false`; successful transport is not
successful configuration validation. Saving configuration or running this
read-only check does not prove Codex/Jules execution. Project deletion is blocked
by retained observation schedules, Work Plans, PR runs or connection-test history;
the source owns these distinct checks rather than a blanket promise of deletion.

## 5. Implementation and verification

Inspected source: `modules/hub/app/features/project_management/projects/schemas.py`,
`modules/hub/app/features/project_management/projects/services.py`,
`modules/hub/app/features/project_management/projects/repos.py`,
`modules/hub/app/features/project_management/projects/usecases/onboarding.py`,
`modules/hub/app/features/configuration/connectors/schemas.py`,
`modules/hub/app/features/configuration/connectors/services.py`,
`modules/hub/app/features/configuration/connectors/crypto.py` and
`modules/hub/app/features/configuration/connectors/usecases/token.py`.
The cited checks were inspected, not freshly executed for this document. Mocked
GitHub responses do not establish real token permissions or live provider access.
