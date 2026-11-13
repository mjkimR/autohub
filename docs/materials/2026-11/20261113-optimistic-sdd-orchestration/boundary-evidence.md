---
id: MAT-optimistic-sdd-boundary
title: SDD ownership removal evidence
summary: "Source-inspected evaluator dependencies, reusable PR mechanisms and open-proposal dispositions for optimistic SDD orchestration."
created_at: 2026-11-13
---

# [MAT-optimistic-sdd-boundary] SDD ownership removal evidence

Source baseline: `9cc90ff27daa15256ea38488464e6330089d8a69` on `main`.
Inspection is separate from executed checks and live deployment evidence.

| Observation | Source | Consequence |
| --- | --- | --- |
| Evaluation restores committed assets with locked sync and a stale-receipt sync fallback. | `modules/hub/app/features/project_management/sdd/runtime.py:164` | Delete restoration; do not replace it with runner setup. |
| Devkit execution resolves the lock runtime before entering OS isolation. | `modules/hub/app/features/project_management/sdd/checkout.py:79` | Removing only installation leaves the controller coupled to evaluation. |
| Native requests tell agents to run one current stage and stop for Hub evaluation. | `modules/hub/app/features/project_management/pipeline_runs/requests.py:28` | Replace stage instructions with intent and repository-owned execution. |
| Ordinary PR implementation observes pushes and durable provider questions. | `modules/hub/app/features/project_management/pipeline_runs/usecases/implementation.py:103` | Reuse this path; preserve question ingestion across push/CI transitions. |
| Draft and project auto-merge policy already guard merging. | `modules/hub/app/features/project_management/pipeline_runs/usecases/ci.py:103` | Start both activity kinds Draft and retain current-head GitHub checks. |
| Batch admission re-previews milestones, compares runtime/config/policy and checks eligibility. | `modules/hub/app/features/project_management/sdd/batch_driver.py:66` | Retire executable milestone/batch admission; no replacement queue is necessary. |
| Both native SDK bridge targets read checkout evidence through the SDD evaluator. | `modules/hub/app/features/execution/flows/bridge.py:88`; `evidence.py:42` | Retire both built-in bindings together; generic SDK flows stay independent. |
| Native snapshots select old progression and control. | `modules/hub/app/features/project_management/pipeline_runs/usecases/progress.py:197`; `control.py:81` | Use an explicit execution discriminator and fence old rows before removing the evaluator. |
| The serving image packages the SDD build environment, uv and bubblewrap. | `docker/hub.Dockerfile:13`; `docker/hub.Dockerfile:47` | Remove only serving artifacts owned by the evaluator. |

The Scout's independent read-only snapshot had tree
`804983b7fc4f815aead18ba2292b3ba0fa38d08f` before and after; HEAD remained
the source baseline. Its return is recorded in historical Git `725317b9e4450a1abfda7d20d0b72571191ce7ed:docs/proposals/PROP-optimistic-sdd-orchestration/envelopes/scout-01.yaml`.

Owning contracts: `CAP-SDD-native-delivery`, `CAP-SDD-workflow-control`,
`CAP-SDD-runtime-isolation`, `CAP-SDK-existing-pr-bridge`,
`CAP-PR-pull-request-delivery`. Reverse-reference queries identify current
architecture, use-case and UX consumers; completed specs retain history.

## Open proposal dispositions

The independent proposal anchors besides this request are
`PROP-jules-antigravity-migration`, `SPEC-owed-counts-error-reason`,
`SPEC-run-origin-links`, `PROP-schedule-config-ownership`,
`SPEC-sidebar-overflow-cues` and `SPEC-updated-at-maintenance`.
There are six, not counting each proposal's target blueprint as separate work.
The proposal list/search and body inspection found no open dedicated runtime or
workflow-evaluation expansion to reject. Runtime and path-source changes are
completed specs. Native batch links in `SPEC-run-origin-links` still apply to
retained history; `SPEC-updated-at-maintenance` is an independent timestamp fix.
Keep their independent outcomes and reconcile their affected SDD assumptions.

## Remaining verification

Development must establish exact migration upgrade/downgrade behavior and stale
worker races, enumerate imports before deleting modules, and regenerate the
public API client. No live GitHub, Actions or provider test was performed in
Planning. Remote branch absence was unverified because origin DNS was unavailable.
