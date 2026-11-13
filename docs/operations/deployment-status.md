# Implementation and verification status

Local implementation and checks were recorded on **2026-11-05**. The last recorded
production baseline is **2026-10-02**, Cloud Run revision `autohub-00015-4l4`, DB
schema `autohub`. Documentation cleanup did not recheck the serving revision or
rerun the historical suites below. These records do not establish an SDD baseline
for Auto Hub's own development. All verification recorded below predates
`SPEC-optimistic-sdd-orchestration`, which removes the embedded evaluator and
retires native batch/bridge execution. No deployment or live canary of that
responsibility change is recorded.

## Current local implementation

| Area | Implemented behavior | Owning reference |
| --- | --- | --- |
| SDD activities | Explicit Planning/Development intent, Draft PR publication and ordinary Run questions/CI; repository agent owns setup/workflow | `CAP-SDD-native-delivery`, `CAP-PR-pull-request-delivery` |
| Retired native execution | Historical runtime/decision/batch evidence and fenced legacy authority; no evaluator runtime | [activity operations](sdd-runtime.md) |
| Repository viewer | Branch-specific documents, proposal roadmap and recorded Proposal → Spec → Run/PR lineage | Viewer (`CAP-DOC-repository-viewer`) |
| Pipeline progression | Shared tick/webhook/manual driver, bounded retries and preserved waits | Advancement (`CAP-PR-pull-request-delivery`) |
| SDK flows | Durable generic host and scoped approval; built-in SDD/PR bridge new effects retired | `CAP-SDK-task-flow-execution`, `CAP-SDK-existing-pr-bridge` |

### Latest recorded local verification

The 2026-11-05 devkit v0.1.6 compatibility follow-up recorded **1,237 backend tests
passed / 17 skipped**, 110 PostgreSQL SDD/bridge checks passed and 215 UI checks
passed. The [local verification report](../materials/2026-11/20261105-delivery-verification/report.md)
retains the pinned revision, primary/follow-up scopes, commands and limitations.
Counts overlap and are not additive. Production deployment and remote GitHub
Actions execution were not performed for that follow-up.

### Remaining rollout evidence

Before claiming deployment of the local changes, build the container, apply the
matching retirement migration, and inspect previously dispatched work under the
[rollout procedure](sdd-runtime.md#rollout-and-rollback). Check ordinary activity
start/questions and GitHub delivery through the [live canary](sdd-runtime.md#live-canary-after-deployment),
and record the revision and exact Run/PR links. Actual provider
replies, GitHub CI and merge behavior cannot be inferred from local fixtures.

## Recorded production baseline (2026-10-02)

The [consolidated production report](../materials/2026-10/20261002-production-verification/report.md)
retains the dated revisions and external evidence for PR implementation/fix/merge,
Work Plan dependencies and controls, Issue synchronization, provider connection
tests, questions/answers/resume, cancellation/replacement and Google account
approval. It also records manual interventions and gaps in live coverage.

The recorded baseline included account/API-key access, the work/operations MCP
split, shared maintenance and retention, and managed Cloud Run deployment.
A maintenance checkpoint succeeded, but actual deletion of expired rows was not
verified. Do not interpret this baseline as deployment evidence for later SDD,
viewer, SDK or toolchain changes.

## Recorded deployed scope without a live canary (2026-10-02)

The following behavior was recorded as deployed with automated coverage only:

- Work Plan backlog and activity (`CAP-WORK-work-plan-execution`): draft/proposed
  states, membership edits, comments and activity history.
- Plan classification (`CAP-WORK-work-plan-execution`): changing a
  group records history without changing execution, state or specifications.

## Excluded and deferred

- Live verification exclusions remain in the [production report](../materials/2026-10/20261002-production-verification/report.md#limitations).
  Later SDD and SDK production canaries remain outstanding.
- Work Plans do not support cross-Plan Item dependencies, failed-Item retry APIs,
  automatic successor substitution, or bulk policy/quota/path controls by group.
- Automatic planning/WBS, dynamic catalog routing, Jules question collection and
  pre-merge LLM review are outside the implemented scope. Provider uncertainties
  remain in catalog limitations (`CAP-AGENT-provider-sessions`).
- Native executable milestone batches and built-in SDD/PR bridge execution are
  retired; no replacement scheduler/bridge is promised (`CAP-SDD-native-delivery`).
- Plan registration issues many queries (query-counter warning); behavior is not
  affected.

Operational procedures belong in [operations](README.md). Product guarantees
belong in their capability contracts rather than being repeated in this status.
