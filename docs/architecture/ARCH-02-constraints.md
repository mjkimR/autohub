---
id: ARCH-02-constraints
title: Architecture constraints
summary: "Defines the repository's code, transaction, credential and compatibility boundaries with the checks or review that enforce them."
status: active
---

# [ARCH-02-constraints] Architecture constraints

## Constraints and enforcement

| Boundary | Constraint | Enforcement |
| --- | --- | --- |
| Backend layering | Router/API modules MUST NOT import repository modules directly. | `RULE-app-router-repo-import`, run by `scripts/check-backend.sh`; this import check does not prohibit the router's direct deep-health reads |
| Transaction ownership | Services MUST NOT commit or roll back their caller's transaction. | `RULE-app-service-commit` |
| Database construction | Router/service code SHOULD use the configured injected session rather than creating a separate engine or session factory. | `RULE-app-db-factory-in-layer` (warning) |
| Shared HTTP client | Feature code MUST NOT close the process-wide shared HTTP client. | `RULE-app-shared-client-close` (warning); shutdown ownership in `app/main.py` |
| SDK isolation | The standalone SDK MUST remain importable without the backend and its database dependencies. | Review only for dependency direction; `packages/sdk/pyproject.toml` and standalone `just test-sdk` / `just build-sdk` |
| UI contract | Authored UI MUST consume the generated typed API and MUST NOT hand-edit its generated declarations. | `just check-ui-api`, UI type checks; review for handwritten client usage |
| Repository responsibility | Hub MUST leave connected-repository setup and workflow interpretation to its repository/agent and MUST NOT introduce an evaluator or sync service. | Source/import, activity request and serving-image inspection; `CAP-SDD-native-delivery` |
| Runtime identity | Python source/override/lock refs and vendored viewer provenance MUST agree with the reviewed devkit pin. | `just check-devkit`, `modules/hub/tests/unit/scripts/test_check_devkit.py` |
| Secrets | Repository documentation and logs MUST NOT expose connector credentials, machine secrets or personal access tokens. | `RULE-secret-leak` checks explicit targets for credential filenames and recognized key patterns; review covers other disclosure and logs |

A warning-level rule records a gap without failing the command. A passing lint
run does not imply every architectural constraint is mechanically enforced.

## Compatibility ownership

`CAP-SDK-task-flow-execution` owns the SDK/host protocol and immutable release
identity. `CAP-SDK-existing-pr-bridge` identifies retired bridge authority.
`CAP-SDD-native-delivery` owns optimistic activity context and retained claims. Changes to one
contract do not silently change the authority of the others.

The installed app-common rules provide layering checks; Auto Hub's own source
remains responsible for its product invariants. Source inspection and a rule's
presence are not substitutes for executing the relevant regression tests.

## Code and command anchors

- [Backend checks](../../scripts/check-backend.sh) run pin, lint, sync and architecture checks.
- [Project recipes](../../justfile) define lint, type, SDK and generated-client checks.
- [Activity execution boundary](../../modules/hub/app/features/project_management/sdd/execution.py)
  distinguishes new descriptive intent from retired native authority.
- [Pin checker tests](../../modules/hub/tests/unit/scripts/test_check_devkit.py)
  exercise supported pin inputs and mismatch failures.
