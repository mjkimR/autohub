---
id: PROP-decision-continuation
title: Follow decisions through explicit continuation
summary: "Connect reviewed decisions to explicit next actions and visible application outcomes without conflating saved answers, approval or resumption."
status: reviewing
created_at: 2026-11-05
target_area: capabilities/delivery/
priority: medium
size: M
planning_effort: high
dev_effort: high
milestone: MS-operator-decisions
depends_on:
  - PROP-operator-decision-inbox
boundaries:
  owns:
    - modules/hub-ui/src/lib/api/
    - modules/hub/app/features/project_management/pipeline_runs/
    - modules/hub/app/features/project_management/sdd/
    - modules/hub/tests/integration/features/project_management/pipeline_runs/
    - modules/hub/tests/integration/features/project_management/sdd/
    - modules/hub-ui/src/lib/features/project-management/pipeline-runs/
    - docs/capabilities/delivery/
    - docs/capabilities/sdd/
    - docs/usecases/delivery/
    - docs/usecases/sdd/
    - docs/ux/delivery/
    - docs/ux/sdd/
    - docs/steering/
  excludes:
    - docs/operations/
    - .github/
    - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-decision-continuation] Follow decisions through explicit continuation

## 1. Background & Hypothesis

Existing contracts intentionally separate saving an answer, applying it, publishing native decisions and authorizing integration. These distinctions protect authority, but completing a decision can leave the operator locating its next step elsewhere. Contextual continuation can make each transition visible and accessible without collapsing those operations.

### Source anchors

`CAP-PR-operator-decisions` requires explicit saved-answer selection for resume. `UX-sdd-workflow-request` states that a recorded worker answer remains open until its envelope is published. `PROP-operator-decision-inbox` supplies the common discovery and navigation entry point this work completes.

## 2. Technical Spike Questions

- **Q1**: Which saved, applied, publication-pending and delivery-pending states can existing owner receipts expose, and where is a read-model extension needed?
- **Q2**: Which next actions are valid for ordinary answers, proposal decisions, worker answers and integration authority without treating them as interchangeable?
- **Q3**: How should unknown outcomes, changed heads, later pauses and replayed requests appear while preserving stable mutation identities?

## 3. Proposed Design & Impact

### Alternatives and decision

| Option | Benefit | Cost and risk |
| --- | --- | --- |
| A: use existing question/attempt/native history views only | No API extension | Ordinary resume receipts are not public; native history caps at 100 and cannot reliably recover a specific lost response. |
| B: read-only owner request outcome plus persistent owner UI, recommended | Exact recovery with existing owner records; preserves authority boundaries | Typed read query and request-intent state in UI; incomplete evidence remains unknown. |
| C: independent continuation ledger or controller | Uniform state machine | Duplicates owner truth and introduces synchronization and authorization drift. |

Choose B. `PADR-decision-continuation-outcomes` records this cross-feature decision. This adds no mutation controller, persistence table or inbox projection.

### Owner outcome read contract

Add authenticated `GET /api/v1/pipeline-runs/{run_id}/decision-outcomes/{request_id}` with required `operation` discriminator: `question`, `answer`, or `resume`. The discriminator chooses the existing owner namespace; identical UUIDs across namespaces never alias. The caller supplies no authoritative actor. Apply the same run/project visibility and history policy as existing decision reads. Missing/inaccessible runs return 404; invalid operation/UUID returns 422. A missing request on an accessible run returns 200 with `record_state: unknown`, never definite failure. The endpoint performs no repository/provider/network call or mutation and returns no request digest or credentials.

Return a typed response with the requested operation/request ID and run ID; `record_state` (`unknown` or `recorded`); current run revision/state and read observation time; and nullable owner evidence: question/answer IDs, applied attempt ID, execution attempt state, delivery state/time, native request/answer channel, publication state/candidate head, resolved envelope evidence, inspected head/digest and current authority/hold. Include only fields supported by the selected owner's persisted records. No generic `completed` flag or action-authority booleans are introduced. Missing/unsupported facts are null with a reason, distinct from known pending or failed evidence. Never infer delivery from attempt preparation, publication from HTTP success, or current approval from a historical receipt.

Query existing question/answer rows and `RunResumeReceipt` by exact request ID and run ownership. Correlate the receipt's existing execution attempt and delivery records; use a consistent database transaction for the response. Do not scan the capped native history list. For worker answers, extend existing owner inspection to retain validated answer-envelope file/identity, `answers_to`, answered question ID, workflow/segment and inspected head alongside the existing native evidence. Current `evidence.reports` omits answer envelopes; add a bounded owner evidence extractor rather than infer resolution from request disappearance. Correlate that exact evidence to the receipt/decision record. Unrelated envelopes, wrong questions/workflows, malformed links and mere request disappearance do not prove publication; retain publication pending or unknown according to available evidence. Refresh replaces the inspection basis under the predecessor CAS and does not grant authority. Delivery/publication failure labels require their respective recorded failure evidence. An ended run keeps its retained outcome visible while its records exist; run retention remains unchanged.

### Explicit continuation and unknown outcomes

The selected owner review remains open after mutation and shows the recorded outcome separately from the current run. Reopening the same run and question/request can reconstruct durable evidence. Save answer never selects or applies an answer automatically. Resume with selected answer requires an explicit saved-answer selection, current revision, matching question/head and existing owner guards. Native Hub clarification follows native control, not ordinary resume semantics. Native worker answer recording remains publication pending until matching envelope resolution is observed. Proposal acceptance publication does not imply handoff, integration approval or merge. Integration authority recorded does not imply workflow completion, delivery or PR merge.

Retain the exact endpoint, owner request ID, actor-bound submission intent and immutable payload for every unresolved operation in the active run-review session. Preserve them through read refresh and temporary dialog close/reopen; never derive a new resume ID from the refreshed revision after an uncertain response. Do not persist answer text/payload in browser durable storage. A browser reload loses unacknowledged in-memory intent; the UI explains that the prior unacknowledged intent is unavailable and recovery is read-only from durable owner history. The unresolved replacement-submission guard applies only while the in-memory intent exists; after full reload, new explicitly reviewed operations rely on existing owner revision/head/authority guards, and the UI makes no recovered-intent guarantee. Existing saved answers/native history provide links to their recorded request outcomes; no promise of automatic recovery for a never-recorded request after reload is made.

After a timeout/lost response, show Outcome unknown and Check outcome. A successful mutation response followed by failed refresh remains recorded-with-refresh-error, not mutation failure. Read errors and missing receipts stay unknown. Permit an explicit Retry same request only using the retained original endpoint and complete payload; unchanged owner replay guards remain authoritative. No background retry, new request ID, changed note, alternate answer or generic native resume is substituted. This permits ordinary save replay's existing refreshed-revision semantics only after an acknowledged save ends the prior intent; uncertain save retry still retains its original payload.

If current head/generation/binding/authority differs, keep the historical outcome visible and disable replay-as-continuation. Use the predecessor's exact-subject inspection/CAS to review a fresh basis before any new action; do not silently rebind the old selection. For uncertain native proposal publication, expose the existing owner reconciliation route explicitly and explain its possible inspection/continuation effect; it is not Check outcome and cannot grant authority or override later stops. A prior successful receipt can be replayed only as its owner permits; the current paused/revoked/canceled state remains authoritative. No automatic dispatch retry is added; delivery recovery routes to existing run controls.

### Candidate acceptance examples and verification

- **E1**: Given an ordinary pending question, when Save answer succeeds, then the saved answer/text/ID remains visible, the run stays stopped, and no answer is preselected for application.
- **E2**: Given an explicitly selected saved answer, when valid resume prepares its attempt, then Applied to attempt identifies that one attempt while delivery is pending/unknown until delivery evidence exists. Native clarification retains its native branch behavior.
- **E3**: Given a recorded native worker answer, when publication has not resolved its exact question, then Answer recorded — publication pending remains visible with duplicate answer controls disabled. A matching envelope resolution changes the disclosure; unrelated envelopes and request disappearance without exact proof do not.
- **E4**: Given proposal preparation/publication uncertainty, when Check outcome reads its original request, then saved intent, candidate publication and current authority are distinct; a later canceled/paused state is never revived.
- **E5**: Given lost mutation response, when reads refresh the revision or the dialog reopens, then an explicit retry sends the original owner ID and payload. A missing receipt/read error stays Outcome unknown, and changed-input submission remains disabled.
- **E6**: Given successful application followed by later pause, when the receipt is replayed, then the UI shows the current pause and the original attempt; no second attempt or resumed execution is created.
- **E7**: Given a changed native head/subject or ordinary question head, when current context loads, then continuation is disabled until fresh exact-subject review; an ordinary stale answer cannot be applied to the new head.
- **E8**: Given integration authority was recorded, when outcome loads after revocation or a hold, then current authority is shown separately from its historical receipt; generic resume is not labelled or submitted as approval.
- **E9**: Given a known request older than the native history cap, when outcome is queried, then exact evidence is returned without scanning history or external calls. A different namespace/run cannot return that request's evidence.
- **E10**: Given a successful save/apply response followed by a read error, then the acknowledged result remains visible with Refresh failed; no replacement mutation appears.
- **E11**: Given unknown/recorded/published/failed delivery states and no external live observation, then labels reflect only persisted owner evidence; no Delivered, Implemented or Completed claim is inferred.

Development adds integration tests for scoped exact lookup, unknown/not-visible/invalid cases, receipt/attempt joins and no external calls; owner tests cover replay after later stop, changed head, publication uncertainty, lost persistence, matching/unrelated answer-envelope correlations, request disappearance and full reload before the durable receipt boundary. UI tests cover the E1–E11 matrix, exact selection, focus/close/reopen, immutable retry payload and response-then-refresh failure. Inspect and extend existing owner tests rather than duplicate their implementation. Run relevant backend/UI tests, typed API generation, `just lint` and `just check` after backend initialization in Development. Planning runs document/envelope checks only. No timing/count improvement is claimed; observable before/after is whether the selected outcome and explicit next step remain accessible.

### Non-goals

- **Scope Excluded**: implicit application, automatic approval, generic resume as native authority, batch approval, new authority ledgers, inbox projection/age/pagination implementation, browser durable storage of decision text, and automatic delivery recovery.
- **Scope Excluded**: provider/SDK/Jules decision support, operations, pilot/deployment/live verification, monitoring and CI changes.

### Planning assumptions and dependency revalidation

The user authorized routine design choices and requested separate UX review. B and the owner-modal arrangement are assumptions within that scope; no business choice blocks this turn. High Development effort remains appropriate because replay, external publication and authority disclosure span persisted owner boundaries.

`PROP-operator-decision-inbox` is accepted but not implemented/completed in this worktree. Its exact-subject selection, first-observed native age, refreshed inspection and CAS persistence are provisional prerequisites, reused without duplication. Before Development or handoff, compare the landed predecessor's exact completed spec and implementation with this bundle, replace the dependency anchor through the normal process, and revise any mismatched fields/routes/UI boundaries. Recheck touched owner tests, generated types and active branch overlap; do not treat this branch's checks as evidence for the eventual landed head.

## 4. Lifecycle & Retirement Criteria

User plan-intent authorizes this high-effort Planning turn. ORDER OVERRIDE: Planning may precede completion of `PROP-operator-decision-inbox`; this exception authorizes Planning only. The accepted inbox design is a provisional dependency, not implemented evidence. No plan-accept or Development handoff authority is supplied. Planning resolves the spike
questions, evaluates the recommended design and drafts affected interactions
before code. The milestone frames the theme without binding the final scope.

The direct prerequisite is `PROP-operator-decision-inbox`. It supplies the shared foundation described above. Eligibility requires its exact completed spec anchor after handoff; update the edge through the normal handoff reference process.

Acceptance and Development handoff follow `sdd-proposal`. Rejection retains
the decision and reason through the proposal lifecycle. This proposal is complete
only through a verified accepted implementation, not from creating this draft.
