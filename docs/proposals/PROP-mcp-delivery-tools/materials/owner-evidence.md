# MCP owner evidence

Read-only inspection at base `0010af5fa2ca053e9023f90689f2cdb37a6bbaf5`; no product tests run.

- `modules/hub/app/mcp/auth.py:40-58`, `registration.py:12-38`, `server.py:14-35`: authenticated machine context, per-tool scopes and disjoint registries.
- `modules/hub/app/mcp/interactions.py:43-54`, `work_plans.py:87-111`: existing `machine:<id>` actor precedent.
- `modules/hub/app/features/project_management/pipeline_runs/usecases/discovery.py:25-36,38-121`: persisted cursor query; exact review has external inspection, writes and CAS.
- `modules/hub/app/features/project_management/pipeline_runs/usecases/outcomes.py:11-32`: exact owner namespace query with coherent persisted evidence.
- `modules/hub/app/features/project_management/sdd/batch_usecases.py:64-195`: existing batch queries and actor/request/revision controls. `batch_repo.py` lists at most 50 rows; claim history itself is not newly database-bounded by this proposal.
- `modules/hub/app/features/project_management/work_plans/usecases.py:149-175`: recovery transaction/actor/history.
- `modules/hub/app/features/project_management/work_plans/replacement_usecase.py:35-267`: exact subject ownership, revisions, actor-bound receipt replay, acceptance/withdraw guards.

Incoming-reference review: `devkit docs refs <ID> --direction in -n 0` inspected `CAP-MCP-tool-access`, `CAP-PR-operator-decisions`, `CAP-SDD-native-delivery`, `CAP-SDD-workflow-control` and `CAP-WORK-work-plan-execution`. The transport capability and `UC-connect-hub-tools` are changed targets; owner contracts and related accepted ADRs remain read authority, with no changed decisions. Existing incoming references include `ARCH-03-system-context`, `ARCH-08-crosscutting-concepts`, `CAP-ACCESS-authentication-authorization`, decision inbox/continuation and Work Item recovery/replacement completed specs, and their owner use cases. Reference lists are discovery evidence, not a claim every referencing document must change.

Options compared: UI-only, scoped focused adapters and raw proxy. Scoped adapters recommended; no unsupported human impersonation, raw snapshot disclosure or owner behavior change is admitted.
