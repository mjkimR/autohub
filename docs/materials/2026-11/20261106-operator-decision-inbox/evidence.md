# Decision inbox source inspection

Planning inspection at source `ac9e7562d5835dd8d8cc380c7203af9544f080a0`; no application tests executed.

- `pipeline_runs/models.py` RunQuestion and `interaction_repo.py` pending: open/answered rows and TimestampMixin; pending is per run, newest question listing is run-scoped.
- `sdd/services.py:208` stores evaluated workflow evidence; `sdd/progress.py:337,413` derives waiting/approval state. `PipelineRun.sdd_progress` is stored JSON and contains no per-request waiting origin.
- `SddWorkflowRequests.svelte:29-41` excludes dev-integration and renders requests[0]. Exact inbox request routing therefore requires an owner UI extension.
- `RunDecisionsDialog.svelte:54-78` reloads questions/run with a revision consistency check, which is a database refresh rather than live native repository evaluation.
- `sdd/api.py:73` exposes read-only readiness inspection. Development must adapt selected-owner evidence refresh without triggering advance or starting work.
- `CAP-PR-operator-decisions`, `CAP-SDD-native-delivery`, `CAP-SDD-workflow-control` and their three target use cases preserve separate save/application/publication/integration authority.

Nested Scout inspected these worktree sources without writes. Database scale, concrete indexes, query plans and fresh migration tests remain Development verification, not Planning claims. No read outside the assigned worktree was reported.

Challenger fold: `sdd/control.py:150-170` dispatches worker answer publication before the answer envelope exists. The worklist therefore retains a disabled publication-pending row through implementing. `sdd/control.py:62-76` compares freshly inspected evidence digest to stored evidence; refresh requires CAS persistence through an owner adapter, not readiness alone. Two P2 findings were self-reverified against the amended design.

UX fold: added native Hub question discovery at `UC-complete-sdd-workflow` 3d and drafted exact object-register row additions. The separate review scores UX-decision-inbox R1–R5=2, R6=1 on the original draft; both findings are addressed in prose for Host review, with no visual testing claim.
