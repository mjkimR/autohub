# Native specrig delivery

Status: completed (locally verified; not deployed)

## Contract

PipelineRun owns native delivery, decisions, attempts, cancellation and merge. The
specrig module interprets CLI output; it does not own another execution engine.
Existing SDK consumers and their paused-PR bridge remain separate.

1. General projects retain their existing behavior. Native enrollment requires a
   spec directory and a configured, exact CLI version. Readiness checks are read-only.
2. Snapshot project mode, repository/spec, CLI version, workflow hash and policy at
   enrollment. Mode-only project changes apply to new runs, not active runs.
3. Evaluate workflow through CLI in an isolated checkout at the observed PR head
   and base. Never infer review completion from a push. Never declare disk checks.
4. Use existing attempts for stage work, existing questions for direction, and
   revision-checked durable resume receipts for approve/revise/reject. Approval
   includes actor, inspected evidence and commit. Repeated commands are idempotent.
5. Integration approval defaults to explicit user action; policy auto may delegate
   the gate but does not enable merging when auto_merge is disabled. A draft after
   approval revokes it. Integration within approved intent may change the head;
   final validation, base ancestry and CLI lint must pass before CI/merge.
6. Final CI and merge remain owned by the existing PR controller. Recheck native
   evidence against current head/base immediately before allowing its merge.
7. UI exposes readiness, spec enrollment, stage/evidence and typed decisions.
8. Verify normal-mode regression, stale/duplicate decisions, rework, revocation,
   base changes and persistence. Live deployment/GitHub writes require a separately
   configured environment and are not implied by local fixture results.

## First delivery boundary

Start from an existing PR with a bound spec. Use the configured GitHub connector
to fetch an isolated checkout; only Git and the pinned specrig CLI run locally.
Agent editing uses existing adapters. Remote scope coordination and old renderer
removal follow actual multi-run/consumer evidence and are outside this delivery.
