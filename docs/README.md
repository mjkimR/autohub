# Documentation guide

Start with the current contract for the task you are doing. Deployment claims and
validation counts belong in [delivery status](delivery-status.md), where the last
recorded production baseline is separate from newer local implementation.

## Start here

| Task | Document |
| --- | --- |
| Check what is implemented, tested or deployed | [Delivery status](delivery-status.md) |
| Connect a devkit repository, select its runtime, or understand SDD ownership | [devkit integration](devkit-integration.md) |
| Browse documents, roadmap members and their executions | [Repository viewer](repository-viewer.md) |
| Start Planning/Development, answer questions, approve or recover a run | [Run decisions](run-decisions.md) |
| Run checks, understand tick timing or operate maintenance | [Development and operations](development.md) |
| Deploy the service and verify its host | [Cloud Run deployment](cloud-run-deployment.md) |

## Current contracts

| Area | Documents |
| --- | --- |
| Engine and GitHub | [Architecture](architecture.md), [CI connection contract](ci-contract.md), [Codex PR mention protocol](codex-pr-mention.md), [CI templates](../templates/github-actions/README.md) |
| Agent admission and connections | [AI catalogs](ai-catalogs.md), [implementation notes and limitations](ai-catalog-implementation-notes.md), [project connection tests](project-detail-and-connection-tests.md) |
| Plans and execution batches | [Work plans](work-plans.md), [backlog and activity](work-plan-backlog.md), [domain design](work-plans-design.md) |
| SDK and external flows | [SDK contract and PR bridge](sdk-task-flow.md), [standalone SDK](../packages/sdk/README.md) |
| Access and notifications | [MCP](mcp.md), [Google authentication](google-auth.md), [operator notices](operator-notices.md), [connector encryption](../modules/hub/README.md#connector-credential-encryption) |

Multiple devkit proposals and milestone-wide execution remain
[deferred](devkit-integration.md#deferred-multiple-proposals-and-milestone-execution).
The roadmap currently supports inspection and individual execution actions.

## Dated evidence and reviews

These documents explain a specific verification run or design review. They do not
establish the currently deployed revision or supersede the current contracts.

| Date | Evidence or review |
| --- | --- |
| 2026-09-21 | [Code hygiene review](code-hygiene-review.md) |
| 2026-09-22 | [PR automation canary](canary-results-2026-09-22.md), [MCP distribution review](autohub-distribution-review-2026-09-22.md) |
| 2026-09-23 | [Work Plan canary](canary-results-2026-09-23.md) |
| 2026-09-28 | [Prompt Issue sync canary](canary-results-2026-09-28.md) |
| 2026-09-29 | [MCP tool review](mcp-tool-review-2026-09-29.md) |
| 2026-10-01 | [Fresh schema and question/answer canary](canary-results-2026-10-01.md) |
| 2026-10-02 | [Control and recovery canary](canary-results-2026-10-02.md) |

## Maintaining these documents

- Keep behavior in its owning contract and link to it from overviews. Runtime
  provisioning belongs in devkit integration; approval semantics in run decisions;
  viewer behavior in repository viewer; check commands in development.
- Keep public command names and defaults aligned with the repository
  [justfile](../justfile). Preserve section anchors used by other documents when
  moving procedures, or leave a short pointer at the old location.
- Update delivery status with the date, tested scope, limits and deployment evidence
  when behavior changes. Do not promote local tests to a production claim.
- Label proposed and deferred work explicitly. Do not document APIs or commands as
  available before they exist, or present a candidate design as a settled contract.
