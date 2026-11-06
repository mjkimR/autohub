# Planning evidence

Source head: `ac9e7562d5835dd8d8cc380c7203af9544f080a0`.
Evidence is source inspection, not test execution or live GitHub observation.

The nested scout read only the assigned worktree and reported no writes or
outside reads. Its comparison informed the option table in the proposal.

## Source anchors

- `CAP-WORK-work-plan-execution`, rules 9 and 13–19, 25, 28: original-target merge release, uncertain-effect reconciliation and failed Run retention. Source: `docs/capabilities/work-plans/CAP-WORK-work-plan-execution.md:48-67`.
- `modules/hub/app/features/project_management/work_plans/models.py:43-72`: one current Item Run link and outcome; no recovery ledger.
- `modules/hub/app/features/project_management/work_plans/execution_repo.py:56-72`: failed preparation excluded from claims; existing leases serialize admitted work.
- `modules/hub/app/features/project_management/work_plans/execution.py:76-80`: definitive preparation refusal records failure, while unknown outcomes retain preparation.
- `modules/hub/app/features/project_management/pipeline_runs/usecases/control.py:91-175`: request replay, revision checks and paused/blocked-only resume. Terminal recovery therefore requires an explicit guarded owner method, not ordinary resume reuse.
- `modules/hub/app/features/project_management/pipeline_runs/models.py:110-153`: durable attempt/delivery identity.
- `modules/hub/tests/integration/features/project_management/work_plans/test_registration.py:67-114`: replacement work leaves original canceled outcome and dependent hold intact.

## Inbound reference inspection supplied to challenger

Scout ran `devkit docs refs <ID> --direction in` before the challenger.

`CAP-WORK-work-plan-execution`: `ARCH-03-system-context`, `ARCH-05-2-components`,
`ARCH-06-execution`, `CAP-MCP-tool-access`, `CAP-PR-operator-decisions`,
`CAP-PR-pull-request-delivery`, `MS-batch-recovery`, `SPEC-work-item-replacement`,
`SPEC-work-item-retry`, `SPEC-ux-documentation`, `UC-execute-work-plan`,
`UX-project-detail`, `UX-work-plan-editor`, `UX-work-plans`.

`CAP-PR-pull-request-delivery`: the common architecture, capability, milestone,
proposal and Work Plan references above, plus `PROP-work-item-replacement-target`,
`PROP-work-item-retry-target`, `UC-deliver-pull-request`,
`ARCH-08-crosscutting-concepts`, `ARCH-11-risks-and-technical-debt`,
`PROP-sdd-milestone-execution-target`, `UX-attach-pull-request`,
`UX-attempt-history`, `UX-dashboard`, `UX-enroll-pull-request`, `UX-pipeline-runs`,
`UX-run-decisions`.

No accepted ADR is changed. `ADR-work-item-recovery-lineage` is a new decision
for durable schema, cross-owner recovery and viable alternatives.

## Verification boundary

Planning validates the authored proposal with devkit rules and envelopes.
Runtime lint/build and PostgreSQL race acceptance checks belong to Development;
no production code changed and no deployed-service assertion is made here.
