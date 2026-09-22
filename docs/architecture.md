# Architecture

## Purpose and Scope

A single Hub manages multiple project connections. Each connection points to one GitHub repository. The number of internal modules within a repository is independent of this mapping.
Hub has no external issue tracker. Work is specified in pull requests the user opens, and its progress is held by Hub's own run state and UI.
The initial implementation begins with PR observation per connection.

## Responsibility Boundaries

| Component | Responsibility |
| --- | --- |
| User | Opens the PR with the task specification and acceptance criteria, enrolls it in Hub, resolves paused runs |
| Hub Core Gate | External state interpretation, next action decisions, deduplication, retries, pause/resume |
| Hub Project Policy | Required workflows/jobs, concurrency limits, revision caps, merge criteria |
| Codex Mention Dispatch | Self-contained implementation/fix requests posted as PR comments, and correlation of their outcomes |
| Codex cloud | Implements the request in its repository environment and pushes to the PR branch |
| Target Repo Actions | Runtime and dependency installation, test environments (e.g. databases), lint/test/build |
| Target Repo | Development guidelines (`AGENTS.md`), tests, project-specific quality standards |

Hub does not checkout target repositories to run arbitrary verification commands.
Project-specific conditions must be expressed through CI checks or review guidelines.
Reusable environment setup is provided via templates, and later through version-pinned reusable workflows.
Branching gates based on repository names or introducing a custom pipeline language are excluded from the initial scope.

Decision logic lives in Hub. Unlike the `g-sandbox` plan to keep verdict logic in the target repository and move only triggers to a hub, Hub owns stage decisions, caps, and merge conditions, while repositories own CI and guidelines.

## Progression Model

The target pipeline is structured as follows. The current implementation scope covers the CI observation stage.

```mermaid
flowchart LR
    PR["User opens PR with task spec"] --> Enroll["Hub: Enroll PR as a run"]
    Enroll --> Mention["Hub: Post @codex implementation mention"]
    Mention --> Agent["Codex cloud: Implement & push to PR branch"]
    Agent --> CI["Target Actions: Verification"]
    CI --> Gate["Hub: Evaluate results & policies"]
    Gate -->|"Fix needed, under cap"| Mention
    Gate -->|"Criteria met"| Merge["Merge; closing keywords close linked issues"]
    Gate -->|"Decision needed / cap or watchdog limit"| Hold["Pause & await user in Hub UI"]
    Hold --> Gate
```

Scheduled tasks inspect the current state, perform bounded necessary actions, and exit immediately.
They do not keep HTTP requests open waiting for long-running Codex executions or CI completions.
The initial version relies on periodic polling; later, GitHub webhooks and periodic recovery will feed into the same observation and evaluation path.

## State Ownership

- `ScheduleConfig` / `ScheduleJob`: When to observe and the single tick execution result.
- Current `TaskState`: The latest read-only observation report. Not an execution history or permanent audit log.
- `ProjectConnection`: The persistent model for the repository, its connectors, the required-job contract, and the last connection check.
- `PipelineRun` / `ExecutionAttempt`: Durable state spanning PR enrollment to merge, immutable request snapshots, idempotency IDs, mention deliveries, external correlation, pause reasons, and retry/recovery history.
- GitHub: Source of truth for PR heads and bodies, comments, check runs, and actual merge status.
- Codex cloud: No task-status API. Hub observes it only through its PR comments and pushes to the PR branch.

A repository maps to exactly one project connection, enforced by a unique constraint on `ProjectConnection`.
`pipeline.observe_project` schedules reference only `project_id` and PR numbers, so the connection is resolved at run time and an edit can never leave a schedule holding a stale contract.
Every edit bumps `revision`; observations and connection checks that started against an older revision are discarded rather than saved.

A partial unique index permits only one active (in-flight, paused, or blocked) run per pull request; different pull requests of a project run in parallel. A project may cap how many of its runs are with an agent or in CI at once (`automation.max_in_flight_runs`): further runs stay queued, and paused or blocked runs hold no slot. Workers use short database leases; acquire, renew, release, and expiry reclamation are conditional writes, and lease tokens are exposed only by lease operations.
Before delegation, Hub commits an immutable request, canonical SHA-256 digest, idempotency key, and correlation marker under the run lease. A retry with the same request reuses that active attempt; a changed request is rejected. The provider port separates this transaction from reconciliation and the later external mutation.

Legacy `pipeline.observe` schedules that still carry their connection inline are migrated explicitly and transactionally through `POST /api/v1/projects/import_schedule`, which keeps the schedule's trigger, PR numbers, enabled state, and history.

## Prerequisites Before Introducing External Writes

Read-only observation stores only the latest report containing timestamps and observed targets.
Because overlapping observations can overwrite earlier runs with later-finishing results, observation alone must never serve as justification for merges.

When introducing external writes:
- Lease mechanisms at the repo/PR/action level and unique idempotency request identifiers must be recorded in the DB.
- PostgreSQL's `FOR UPDATE SKIP LOCKED` during schedule selection only controls schedule selection—it does not guarantee exactly-once execution against external APIs.
- Even if a process crashes after an external request succeeds but before the DB commit, it must be able to find the posted comment by its marker and resume instead of posting again.
- Never run concurrent, competing progression gates inside GitHub Actions.

The execution path is a Codex task started by an `@codex` comment on the enrolled PR, following the protocol proven in `g-sandbox` (D-013, D-017) and specified in [Codex PR Mention Protocol](codex-pr-mention.md). Two constraints shape the design:

- The mention must be posted with a user PAT whose GitHub account is linked to Codex. Mentions from the Actions `GITHUB_TOKEN` get no response, and bot pushes do not trigger CI.
- Codex does not reliably push to the existing branch on its own. Its environment carries a repository-scoped `GH_TOKEN`, and every mention includes an explicit push command for the PR branch.

GitHub remains the source of implementation artifacts: a Codex reply alone does not prove that code was pushed. Hub treats a change of the PR head away from the head recorded in the request marker as the implementation signal, then evaluates CI on that head.

Workspace Agents API triggers published ChatGPT workspace agents and is not a Codex cloud task API. `openai/codex-action` in the target repository's Actions remains the fallback adapter if the mention path becomes unusable; it keeps the same run, attempt, lease, and idempotency contracts but bills an OpenAI API key.

Immediately prior to merging, the latest PR head and base, draft status, and required CI jobs must be re-verified.
Automatic merges must not rely solely on CI passing at the time of an earlier observation.

Approval uses the PR's explicit `draft` flag: work happens in draft, and the operator
marks it ready for review to authorize automatic merging after required CI passes.
An already non-draft PR counts as approved; converting it back to draft revokes
that approval. Hub does not change draft status. This is a PR-level approval,
not a separate review for each new commit; subsequent pushes still require fresh CI.
Draft PRs with missing or skipped CI wait with an approval notice; failed code jobs
can still receive CI fixes while draft. A ready transition wakes the existing run
through the PR webhook, with polling as a fallback. `auto_merge=false` still disables merging.

Branch Protection Rules and required reviews are **unused in the personal-repository
workflow**. Their defensive refusal handling remains for compatibility; deletion or
formal deprecation is deferred. Hub does not configure or bypass repository rules.
After checking `draft`, Hub handles GitHub's `mergeable_state` as follows:

| `mergeable_state` | Hub's action |
| --- | --- |
| `dirty`, `behind` | The branch conflicts with or trails its base: one `conflict-fix` request asks the agent to merge the base in (unless `auto_fix_conflicts` is off). No merge is attempted. |
| `draft` | Approval is pending. The run stays in `awaiting_ci`, explains the ready-for-review action, and rechecks every 5 minutes. The explicit `draft` flag takes precedence over other mergeability states. |
| `blocked` | Compatibility fallback for an externally configured repository rule. The run waits with a repository-rule notice; no conflict fix is dispatched. This is not Hub's approval mechanism. |
| anything else, or not computed yet | Hub asks GitHub to merge the verified head. A refusal (HTTP 405/409) is classified by re-reading the state: only `dirty`/`behind` goes to the agent, everything else waits as above. |

A waiting run is deliberately not paused: resuming a paused run replays its last request to the agent, and nothing here is the agent's to redo.

## GitHub Failures

The GitHub client classifies a failed response from its status and rate-limit headers, never from its body.

| Kind | Signal | Scheduled tick |
| --- | --- | --- |
| `rate_limited` | 429, or 403 with `Retry-After` or `X-RateLimit-Remaining: 0` | The run's `next_action_at` moves out by the delay GitHub names (60 seconds to 1 hour). Not a failure. |
| `auth` | 401 | The run keeps its state, records that the connector's token was rejected, and is rechecked every 15 minutes; it continues by itself once the token is replaced. Not a failure. |
| `upstream` | anything else | The tick's job fails, as before. |

A run holding a reason while in flight is announced once through [Operator Notices](operator-notices.md), like a stopped run. An AI catalog that cannot take more work yet (a quota hold, its concurrency limit) is backpressure, not a failed job. API calls made by a person still return these errors directly.

## Elements Adopted from g-sandbox

We adopt principles such as the PR snapshot → decision structure, missing task reclamation, bounded revision counts, pause/resume semantics, and reuse of existing PRs/requests.
From its PR gate we also adopt the Codex mention protocol: user-PAT mention identity, self-contained prompts with an explicit push block, head-movement completion detection, trusted-author marker filtering, and the silent/usage-limit watchdog.
However, external issue-tracker backlogs and HITL queues, stub PR creation, `notes/*.md` project discovery, Godot installation / direct execution of `check.sh`, planning/prototype/maturity policies, and repo-specific marker compatibility are not part of the core migration scope.

## Isolated connection-test recipes

`project_management/connection_tests` owns a separate lifecycle and ledger from development runs.
`adapters/registry.py` resolves a `(catalog kind, adapter key)` to a recipe implementing
`prepare`, `dispatch`, `observe`, and `cleanup`. Serializable recipe metadata supplies the
prerequisites, phases, and evidence links returned by `/projects/{id}/connection-tests/options`.
The UI renders that contract. Add a recipe and registry entry for another test flow; do not
add provider switches to the common lifecycle or project view. A new catalog kind still needs
its normal quota policy and execution capabilities. Increment the recipe version when its
verification contract changes.

Connection fingerprints cover recipe version, connector identity/credential version, repository,
activation, and CI contract. Runtime quota and display names are excluded. Only the final hash is
exposed; cloud-side settings remain observable only through a real test. Provider clients live in
`ai_catalogs/providers`, so production and diagnostic Jules sessions share Source resolution
without importing scheduler task-registration packages.

Claims persist before external I/O; state and delivery/quota events commit together only for
the current lease. Create-once recipes persist intent before a request and reconcile uncertain
responses without repeating creation. Cancellation uses a row lock when committing observations.
Execution capacity is released once provider completion is observed, independently of CI and
cleanup. Unknown canceled executions hold capacity for at most 24 hours. Jules cleanup closes
positively identified PRs through GitHub before attempting provider reconciliation. Ownership
requires a session output URL or the exact per-test marker, plus repository/ancestry validation.
Codex owns its reserved branch PR. Confirmed PRs receive an HTML body marker and the
`autohub-connection-test` label; metadata failures are warnings and persisted identity still protects them.
Discovery scans recent PRs across bases with a page/time budget. Ancestry alone only quarantines
a candidate for merge blocking; it never authorizes marking, closing, or deleting. Legacy records
without ownership proof are revalidated before mutation. Incomplete scans cannot complete cleanup. Provider reconciliation has a separate timeout within the step
budget so an outage leaves time for GitHub cleanup.

Known test PR IDs remain excluded from enrollment and final merge authorization permanently.
Ancestry checks protect unconfirmed output until reconciliation, including after the 24-hour
branch-retention period, with a bounded pending set; completed history adds no GitHub comparison
calls to normal PRs. Unconfirmed sessions retain their isolated branches and cleanup schedule.
A confirmed terminal session with no PR also resolves output discovery. Cleanup outcome is
separate from test outcome. External jobs are not forcibly canceled, and output recreated after
confirmed completion and cleanup is not guaranteed to be collected.

Recipes opt into manual cleanup resolution through `manual_cleanup_resolution`. Terminal Jules
tests with uncertain creation/output expose a review action. The operator must confirm no remote
work is running or can resume, provide a reason, and review every unconfirmed PR as unrelated.
The API locks the row, rejects active leases and changed candidate SHA sets, and records an
idempotent request ID, reason, timestamp, and reviewed heads in evidence. It fences expired leases
and rechecks GitHub without repeating session creation or changing the test result. Reviewed
heads remain untouched; changed/new candidates require another review. The 24-hour retention
still applies. Confirmed test PR identities cannot be dismissed.

Connection-test schedules reject generic schedule create/update/delete operations. Connectors
referenced by running tests or unfinished cleanup cannot be deleted, even after a project or
catalog switches connectors. Creation and connector deletion use the same connector row locks;
completed history does not prevent deletion of otherwise unused connectors.
