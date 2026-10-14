# SDK task and flow remote contract

## Current scope

autohub-sdk 0.2.0 in `packages/sdk` provides sequential flow declarations and an HTTP client in addition to the existing local pipeline and manifest v1. The real autohub backend implements the release catalog and task-runs APIs and a DB-backed flow executor. The SDK contract is verified against the `mock/autohub` HTTP stub in planhub's separate environment and against loopback HTTP and DB integration tests on the real backend. Production deployment is separate. Python 3.13+ is required, and Pydantic is the only runtime dependency.

## Definition and deployment

FlowManifest v2 contains the existing PipelineSpec in the TaskSpec role and FlowSpec. TaskStep inputs are literals or path references to run or earlier task outputs, and execution moves to the next step in order. ApprovalStep declares a deadline and optional revise_to and max_revisions. FlowSpec specifies result_step. The SDK rejects duplicates, unsupported task references, references to future outputs, and invalid returns. There is no static check of individual fields or schema assignability; the host resolves references and validates the actual input and output schemas.

ReleaseSpec bundles a manifest with exactly one binding per task. A binding is an http/native executor and a target reference and contains no Python code. Definition registration is separate from worker deployment. The host checks the managed machine key and provider/environment ownership and allows only bindings configured on the server. The mock supports only native mock.echo.

## HTTP contract

| Operation | SDK method | Path |
| --- | --- | --- |
| Register release | register_release | PUT /api/v1/task-providers/{provider}/environments/{env}/releases/{release_id} |
| Activate | activate_release | POST release path above/activate |
| Run | start_run | POST /api/v1/task-runs |
| Get | get_run | GET /api/v1/task-runs/{run_id} |
| Control | command | POST /api/v1/task-runs/{run_id}/commands |

The same release ID and digest is idempotent; different content conflicts. Activation checks expected_revision. RunRequest uses provider, environment, task contract, inputs, and idempotency_key. The same key and content return the same run; changed content conflicts. An in-progress run keeps the release ID, digest, definition, and binding snapshot taken at admission.

RunCommand carries command_id, expected_revision, and approve/revise/cancel/resume. Resending a command returns the original receipt; changing content under the same ID conflicts. The run revision increments on every state transition. AttemptView provides step, number, status, input, output, and error; RunView provides release snapshot identifiers, status, current step, wait reason, attempts, and result. Retries and revise visits consume the cumulative task step attempt limit.

Following the existing host convention, the client sends X-API-Key and performs no redirects or automatic retries. AutoHubError exposes the HTTP status and error code, and network timeouts propagate. Separately from general approval, the PR bridge checks the approving actor, revision, evidence digest, and head.

## Execution ledger and recovery

The SDK does not own a DB or scheduler. The existing internal scheduler @task, Work Plan/Item, and PR PipelineRun are separate from external SDK tasks and flows. Separate `sdk_flow_*` tables store environments, releases, runs, steps, attempts, and command receipts. The dispatch intent is committed first, and the worker is called outside the DB transaction. A 60-second lease and revision-conditional writes block late results. When a response is uncertain, the host looks up the existing attempt and resubmits under the same ID only after the worker explicitly confirms that the ID is absent. The existing PR executor and the flow executor do not control the same PR concurrently.

The SDK contract and planhub mock are tracked in specs/2026-10/20261009-sdk-task-flow-contract. The durable host is tracked in the [implementation spec](../specs/2026-10/20261009-durable-sdk-host/spec.md). The planhub application and specrig/PR bridge are implemented locally; production verification and scope linkage connect to F3~F4 of workbench's `docs/planhub-autohub-task-flow-design.md` and planhub PROP-autohub-delivery-host. Existing single-pipeline consumers can keep using manifest v1 and local execution.


## Authentication and execution targets

Use the `X-API-Key` issued by the management API. `autohub:task:write` is required for registration, activation, runs, and control, and `autohub:task:read` for reads. approve/revise require both write and `autohub:task:approve`. A provider/environment is owned by the machine that first registered it, and key rotation on the same machine preserves ownership. The command ledger records the machine/key actor and the receipt. A general approval command does not replace verification of the PR head and review evidence.

The native executor supports `autohub.identity` and the server-allowlisted `autohub.sdd:<name>` and `autohub.pr_delivery:<name>`. HTTP worker configuration and protocol follow the [development guide](development.md#sdk-flow-host). Registration does not deploy worker code. Host limits are 64 characters for provider/environment, 256 characters for task key, 128 characters for step ID, a positive 32-bit integer for contract version, and 1 year for approval deadline. JSON Schema uses draft 2020-12, and external `$ref` is rejected.

`System maintenance` advances up to 32 runs by one step each. GET and run admission do not execute workers. The approval deadline is also checked when a command is received, and the expiry transition is recorded by the next maintenance. The next external polling time is at least 5 seconds later, but the actual progress interval follows the dispatcher tick. Cancellation stays `canceling` until the external worker's terminal result is confirmed; transport errors and generic 404s are not used as evidence of termination.

## planhub PR bridge

The first domain flow in the [implementation spec](../specs/2026-10/20261009-planhub-pr-bridge/spec.md) verifies devkit-spec evidence in the actual checkout and, after explicit approval, resumes and observes a paused PipelineRun already implemented externally. It does not create a new PR or executor. The server allowlist pins the provider/environment, project, and absolute checkout path to the release binding.

The run wire extension `expected_release_id` and `expected_release_digest` checks the currently active release and rejects a run of the wrong definition with 409 before admission. SDK 0.2.0 requests that omit the fields keep the existing contract. planhub passes the fields through a Pydantic RunRequest subclass and pins the SDK dependency to an existing pushed commit.

It checks a clean Git HEAD and, through the real `devkit workflow show/next --unit <spec> --format json`, review, resolved reconcile, completed spec, final-report, and the human gate. The PR claim is unique in the DB and stores the actor, revision, and evidence digest of the command issued with the approve scope. Defining only the delivery step cannot bypass approval. Before resuming, it rechecks the evidence, GitHub head, and PR revision and uses the attempt ID from the existing Resume receipt. A worker restart recovers the same receipt.

PR ready, CI, and merge are owned by the existing PipelineRun owner. The flow projects pending, paused/blocked errors, and terminal results. Cancellation stops control through a claim tombstone and cancellation of the existing run, and does not roll back external agent requests or effects already posted. CLI/git and checkout placement are separate, and this fixture verification does not mark live GitHub CI/merge or the full development workflow integration as complete.

Existing `autohub.specrig:<name>` bindings are preserved as history. The new runtime registers a new immutable release that uses `autohub.sdd:<name>`. Earlier releases or execution evidence are not fixed in place and treated as compatible.
