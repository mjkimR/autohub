---
id: MAT-sdd-milestone-execution
title: Sequential SDD batch design evidence
summary: "Source inspection and alternatives supporting an immutable execution selection delegated to existing native activity owners."
created_at: 2026-11-05
---

# [MAT-sdd-milestone-execution] Sequential SDD batch design evidence

## Scope and observation

Planning base: `448247462d8d54d227eae7e68a70c762de12d46a`; first boundary: `bb7c5e1e65e235e883c10cb699577dbc97ba70d3`. Source inspection is not test execution. Readiness is accepted and unimplemented. Codex isolation is emulated: absolute worktree reads, explicit approvals for each sibling write/shared Git operation and pre/post delegate snapshots substitute for a native guarantee. Scout reported no outside-worktree reads; its identical trees were `117c54273e3550dab688371119b91761faaa9619`.

## Incoming-reference search

Scout started with incoming refs; the caller retained a full `devkit docs refs <ID> --direction in -n 0` recheck. `CAP-SDD-native-delivery` returned 30 references, `CAP-SDD-workflow-control` 23, `CAP-SDD-runtime-isolation` 15, `CAP-EXEC-scheduling-maintenance` 21 and `ADR-sdd-development` 0. Relevant current owners include `ARCH-06-execution`, `ARCH-08-crosscutting-concepts`, `UC-start-sdd-activity`, `UC-decide-sdd-proposal`, `UC-complete-sdd-workflow`, `UX-sdd-proposals`, `UX-sdd-run`, `UX-sdd-execution`, `UX-run-decisions` and `UC-run-due-work`. The results also list the source proposal and readiness drafts; other proposals are outside this worker's body-read scope. No ADR override is proposed.

## Alternatives

| Option | Evidence | Cost/risk | Recommendation |
| --- | --- | --- | --- |
| Separate SDD ledger delegated to native owners | `CAP-SDD-native-delivery` rules 4–6, 17; `CAP-SDD-workflow-control` rule 21; `activities.py:101-214` | New durable claim/control/recovery tables and expected-base seam | Choose: preserves ownership and exact unit evidence. |
| Reuse Work Plan | `work_plans/execution.py`, `WorkPlanExecution.prepare`; native binding in `CAP-SDD-workflow-control` rule 1 | Unbound SDD enters attention; copying units changes scope/authority | Reject for this feature. |
| One PipelineRun for batch | `pipeline_runs/models.py:60-103`; native per-PR enrollment in `activities.py:202-214` | One-PR identity cannot carry several independent proposal/spec approvals | Reject. |
| Eligible-only durable subset | `SPEC-sdd-milestone-readiness` Planning decisions 6–8 | Cannot select dependency-held chain for future intent | Keep for read-only preview only. |
| Explicit future-intent execution subset | Same pinned complete graph, plus exact dependency-held members | Additional selection surface and honest repair/wait states | Choose for execution; all future starts remain freshly gated. |

## Source evidence and failure windows

`activities.py:101-168` resolves a base and invokes start policy before branch creation. `activities.py:118-130` recovers an owned marker-bearing open PR but refuses an unrelated existing branch. Its branch-only failure window needs recorded initial-commit ownership rather than pretending the marker alone recovers every crash. `activities.py:202-214` enrolls after PR creation, so enrollment response loss needs a durable claim and exact run lookup. `CAP-SDD-native-delivery` rules 10–16 fence decisions and uncertain publication. `CAP-SDD-workflow-control` rules 12, 16 and 19 preserve worker holds, bounded handoff and changed-base reintegration. `CAP-SDD-runtime-isolation` rule 9 forbids silent rebinding. `ARCH-06-execution` delegates maintenance to domain owners.

Inspected enforcing-test entrypoints: SDD `test_activities.py`, `test_native.py`, `test_cli.py`, `test_lineage.py`, `test_plan_publication.py` and `test_plan_authorization.py`. They are regression starting points, not evidence that the proposed batch reservation, recovery or PostgreSQL races already pass.

## Unverified areas and Development admission

Exact devkit canonical handoff mapping must be confirmed against the landed predecessor/runtime. A batch ledger's known handoff origin never creates such a mapping. PostgreSQL lock ordering, cross-entry reservations, schema migrations, retention and bounded maintenance need implementation fixtures. Compare the landed readiness SPEC/contract before accepting Development scope. No product tests, live provider, deployment or operational checks were executed by Planning.
