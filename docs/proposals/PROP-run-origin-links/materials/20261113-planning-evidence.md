---
id: MAT-run-origin-links-planning
title: Run related-origin and Repository address evidence
summary: "Head-pinned reverse-link cardinality, read projection and retained-batch selection evidence for run-origin-links Planning."
created_at: 2026-11-13
---

# [MAT-run-origin-links-planning] Run related-origin and Repository address evidence

Inspected head: `e1a50a8064597d65fd44906f1b65c01ad93c2425`. The later Planning commits change only this proposal bundle.
No backend/UI tests or live services were executed for this source inspection.

| Observation | Source | Planning consequence |
| --- | --- | --- |
| Work Item links to one run with a unique nullable FK and a Plan ID. | `modules/hub/app/features/project_management/work_plans/models.py`, `WorkItem` | Derive the Work Plan and Work Item together without storing a second owner. |
| Provider sessions index run ID without uniqueness and retain catalog ID plus optional URL. | `modules/hub/app/features/ai_catalogs/models.py`, `AICatalogSession` | Return a collection; preserve an unavailable URL as text rather than inventing an exact local destination. |
| SDD claims have optional run/member IDs; only the member reaches a batch, and uniqueness is per project/request or live unit/activity. | `modules/hub/app/features/project_management/sdd/batch_models.py` | Preserve multiple claims; individual claims have no batch and need no batch lookup result. |
| The run has an SDD snapshot but no original enrollment-channel field. Lifecycle enrollment and Work Plan dispatch build runs through different paths. | `modules/hub/app/features/project_management/pipeline_runs/models.py`, `usecases/lifecycle.py`; `work_plans/execution.py` | Related evidence cannot distinguish manual, webhook and SDK entry transport. Do not infer it. |
| Run query use cases serialize ORM rows while their caller-owned transaction remains open. The run repository already imports AI-catalog and Work Plan owners. | `modules/hub/app/features/project_management/pipeline_runs/usecases/queries.py`, `repos.py` | Batch enrichment can share one session without new feature edges or N+1 serialization I/O. |
| Project page passes only tab; Repository resets selected unit and initializes the viewer at docs/. | `modules/hub-ui/src/routes/projects/[projectId]/+page.svelte`; `projects/ProjectDetailView.svelte`; `repositories/RepositoryView.svelte` | Thread validated query selection into both viewer and execution panel, preserving mode changes and rejecting stale responses. |
| Batch listing is latest 50, but exact detail lookup is project-scoped and reports 404 for an absent batch. | `modules/hub/app/features/project_management/sdd/batch_repo.py`, `batch_usecases.py`, `api.py` | Fetch the addressed batch by detail instead of searching only the bounded list. |
| The batch store already guards project/generation and monotonic revisions, and list merge preserves selected batch when present. | `modules/hub-ui/src/lib/features/project-management/repositories/sdd-batches.svelte.ts` | Extend these guards for address changes rather than building another batch store. |
| Run next-step component pages through all Work Plans; Attention drops batch ID when constructing its link. | `modules/hub-ui/src/lib/features/project-management/pipeline-runs/run-page/RunNextStep.svelte`; `attention/owed-links.ts` | Consume returned Work Item IDs and one shared Repository subject-link helper. |

Owning contracts inspected: `CAP-PR-pull-request-delivery`, `CAP-SDD-native-delivery`, `CAP-DOC-repository-viewer`,
`UX-run-page`, `UX-pipeline-runs`, `UX-repository`, `UX-sdd-batch`, `UC-deliver-pull-request`,
`UC-inspect-repository-documents` and `UC-execute-sdd-batch`.

The at-most-three extra SELECT count is a proposed Development acceptance bound, not a measured performance result.
Development can compare the same paginated fixture with origin projection enabled/disabled in its own worktree;
no base checkout or machine timing comparison is needed.
