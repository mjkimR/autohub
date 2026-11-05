# Replacement Planning evidence

## Source and baseline

Base: `448247462d8d54d227eae7e68a70c762de12d46a`. Planning-only
prerequisite-order override by user; `PROP-work-item-retry` and
`PADR-work-item-recovery-lineage` are accepted direction, not completed spec.
No moving Development worktree was read. Emulated role enforcement uses absolute
cwd/read scopes, no child writes, sequential children and final boundary diff;
there is no native path-level guarantee.

Source inspected, product tests not executed:

- `CAP-WORK-work-plan-execution` rules 1, 9, 12, 19, 25, 28 and replacement
  interfaces preserve graph, outcomes and retained evidence.
- `modules/hub/app/features/project_management/work_plans/execution_repo.py:23-46`
  owns project serialization and separate Plan/Item holds.
- `modules/hub/app/features/project_management/work_plans/execution.py:187-209`
  owns merge-confirmed success and all-Item Plan completion.
- `modules/hub/tests/integration/features/project_management/work_plans/test_registration.py:67-113`
  owns the descriptive replacement no-release regression.
- `PROP-work-item-retry` recovery eligibility/identity and
  `PADR-work-item-recovery-lineage` outcome clauses constrain the provisional
  history foundation. Revalidate against its landed completed spec before handoff.

## Incoming references inspected by Scout

`CAP-WORK-work-plan-execution` incoming references (17):
`ARCH-03-system-context`, `ARCH-05-2-components`, `ARCH-06-execution`,
`CAP-MCP-tool-access`, `CAP-PR-operator-decisions`,
`CAP-PR-pull-request-delivery`, `MS-batch-recovery`,
`PADR-work-item-recovery-lineage`, `PROP-work-item-replacement`,
`PROP-work-item-replacement-target`, `PROP-work-item-retry`,
`PROP-work-item-retry-target`, `UC-execute-work-plan`, `UX-project-detail`,
`UX-work-plan-editor`, `UX-work-plans`. Counts include multiple occurrences;
these are source IDs reported by the index, not authorization to read other proposals.

`CAP-PR-pull-request-delivery`: all 29 incoming entries fetched with `-n 0`;
relevant ownership sources are the Work Plan capability/use case, delivery/PR
controls, execution architecture and retry foundation. The replacement design
changes none of their PR authority. Scout found no touched accepted ADR;
`PADR-work-item-recovery-lineage` incoming refs are `PROP-work-item-retry` and
`PROP-work-item-retry-target`. `ADR-sdd-development` incoming query was empty.

## Options and evidence limits

Typed per-edge acceptance was compared with descriptive-only registration and a
general graph in the proposal. Only typed acceptance meets exact existing-edge
release while preserving original outcomes. No performance claim or external
verification is made. Migration/locking/API details remain provisional until the
prerequisite is landed; Planning checks do not attest a future landed head.
