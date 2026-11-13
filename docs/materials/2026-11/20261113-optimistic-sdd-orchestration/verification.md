---
id: MAT-optimistic-sdd-verification
title: Optimistic SDD execution local verification
summary: "Executed local backend, PostgreSQL, UI, SDK and static checks for repository-owned SDD execution, separate from live GitHub/provider and deployment evidence."
created_at: 2026-11-13
---

# [MAT-optimistic-sdd-verification] Optimistic SDD execution local verification

`SPEC-optimistic-sdd-orchestration` retains the acceptance scenarios and review
records. Checks below ran on the implementation worktree; the build commit and
review envelope retain its Git identity. The ordinary GitHub/provider boundaries
use controlled HTTP fixtures. No live remote activity, deploy or serving-image
rollout was performed.

| Executed check | Result |
| --- | --- |
| `PYTEST_WORKERS=4 just test` | 1207 passed, 25 skipped; complete backend SQLite suite after independent review fixes |
| `PYTEST_WORKERS=0 just test-pg tests/integration/features/project_management/sdd tests/integration/features/project_management/pipeline_runs tests/integration/migrations tests/integration/features/execution/flows` | 235 passed before the final claim-reconciliation test refinement |
| `PYTEST_WORKERS=0 just test-pg tests/integration/features/project_management/sdd tests/integration/migrations/test_retire_native_sdd.py tests/integration/features/project_management/pipeline_runs/test_optimistic_sdd.py` | 30 passed after the independent publication-ownership and recovery refinements |
| Full UI suite | 64 files, 547 tests passed |
| `just lint` | Passed Python, project/document rules, SDK and UI lint |
| `just check` | Passed backend/SDK types and UI types/build |
| `just check-ui-api` | Generated contracts current |
| `just test-sdk` | 27 passed; loopback fixture required host socket access |
| `just build-sdk` | Wheel and source distribution built |

The 25 SQLite skips include PostgreSQL-only cases, which the dedicated commands
exercise. The PostgreSQL suites used isolated Testcontainers; no shared database
or deployed service was modified. Backend/SDK HTTP fixtures needed localhost
socket access outside the filesystem sandbox. Initial failures caused by sandbox
socket denial were rerun with that test access; they are not passing test results.

UX drafts received independent review before UI implementation. Ownership-conflict
recovery, frozen unknown intent and interface mappings were folded into the
screens and implementation. Component tests establish UI state/request behavior;
no rendered-browser walkthrough was performed.

Serving-image verification inspected the Dockerfile and CI definitions; no full
Docker image build or live GitHub Actions/provider canary was performed. The four
superseded ADRs remain retained history. Related open proposals keep independent
outcomes and no dedicated open evaluator proposal was rejected.

## Independent Review Corrections

The first code-review round reproduced a direct-enrollment ownership gap before
fixing it: the missing-PR-number regression failed while its saved-number case
passed. The final enrollment transaction now matches the observed candidate
branch while excluding only its validated admission. Both cases pass, including
PostgreSQL coverage. Uncertain publication errors now retain the exact claim
inspection reference needed by the existing UI recovery panel.

The required type check caught a raw Python boolean passed as a SQL predicate;
the exclusion is now appended conditionally. `just check` passes after that fix.
Historical project-scoped handoff lineage coverage was restored using an
evaluator-independent fixture. The independent reviewer records remain with the
spec and do not claim live GitHub behavior.
