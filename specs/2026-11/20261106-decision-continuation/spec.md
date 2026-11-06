---
id: SPEC-decision-continuation
title: Follow decisions through explicit continuation
summary: Connect reviewed decisions to explicit next actions and visible application outcomes without conflating saved answers, approval or resumption.
status: completed
created: 2026-11-06
depends_on:
  - SPEC-operator-decision-inbox
related_capabilities: []
related_usecases: []
workflow: sdd-spec-feature
---

# [SPEC-decision-continuation] Follow decisions through explicit continuation

## 1. Problem Statement & Motivation

Handed off from proposal PROP-decision-continuation on 2026-11-06.
- **Preserved Materials**: `docs/materials/2026-11/20261106-decision-continuation`
- Target Docs Blueprint: `PROP-decision-continuation-target` (Living Spec targets for this plan and reconcile.md)

### 1. Background & Hypothesis

Existing contracts intentionally separate saving an answer, applying it, publishing native decisions and authorizing integration. These distinctions protect authority, but completing a decision can leave the operator locating its next step elsewhere. Contextual continuation can make each transition visible and accessible without collapsing those operations.

#### Source anchors

`CAP-PR-operator-decisions` requires explicit saved-answer selection for resume. `UX-sdd-workflow-request` states that a recorded worker answer remains open until its envelope is published. `SPEC-operator-decision-inbox` supplies the common discovery and navigation entry point this work completes.

## 2. User Stories

- **US-1**: As an operator, I want retained decision outcomes and explicit continuation so that saved answers, publication and current execution remain distinguishable.

## 3. Non-Goals

1. **Scope Excluded**: New mutation controllers, automatic approval/application/retry, durable browser answer storage, inbox projection changes, SDK/provider work and deployment.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Retain decision outcome E1

- **Given** an ordinary pending question
- **When** Save answer succeeds
- **Then** the saved answer/text/ID remains visible, the run stays stopped, and no answer is preselected for application.

### [AC-02] Retain decision outcome E2

- **Given** an explicitly selected saved answer
- **When** valid resume prepares its attempt
- **Then** Applied to attempt identifies that one attempt while delivery is pending/unknown until delivery evidence exists. Native clarification retains its native branch behavior.

### [AC-03] Retain decision outcome E3

- **Given** a recorded native worker answer
- **When** publication has not resolved its exact question
- **Then** Answer recorded — publication pending remains visible with duplicate answer controls disabled. A matching envelope resolution changes the disclosure; unrelated envelopes and request disappearance without exact proof do not.

### [AC-04] Retain decision outcome E4

- **Given** proposal preparation/publication uncertainty
- **When** Check outcome reads its original request
- **Then** saved intent, candidate publication and current authority are distinct; a later canceled/paused state is never revived.

### [AC-05] Retain decision outcome E5

- **Given** lost mutation response
- **When** reads refresh the revision or the dialog reopens
- **Then** an explicit retry sends the original owner ID and payload. A missing receipt/read error stays Outcome unknown, and changed-input submission remains disabled.

### [AC-06] Retain decision outcome E6

- **Given** successful application followed by later pause
- **When** the receipt is replayed
- **Then** the UI shows the current pause and the original attempt; no second attempt or resumed execution is created.

### [AC-07] Retain decision outcome E7

- **Given** a changed native head/subject or ordinary question head
- **When** current context loads
- **Then** continuation is disabled until fresh exact-subject review; an ordinary stale answer cannot be applied to the new head.

### [AC-08] Retain decision outcome E8

- **Given** integration authority was recorded
- **When** outcome loads after revocation or a hold
- **Then** current authority is shown separately from its historical receipt; generic resume is not labelled or submitted as approval.

### [AC-09] Retain decision outcome E9

- **Given** a known request older than the native history cap
- **When** outcome is queried
- **Then** exact evidence is returned without scanning history or external calls. A different namespace/run cannot return that request's evidence.

### [AC-10] Retain decision outcome E10

- **Given** a successful save/apply response followed by a read error
- **When** the acknowledged result remains visible with Refresh failed; no replacement mutation appears.
- **Then** Given a successful save/apply response followed by a read error, then the acknowledged result remains visible with Refresh failed; no replacement mutation appears.

### [AC-11] Retain decision outcome E11

- **Given** unknown/recorded/published/failed delivery states and no external live observation
- **When** labels reflect only persisted owner evidence; no Delivered, Implemented or Completed claim is inferred.
- **Then** Given unknown/recorded/published/failed delivery states and no external live observation, then labels reflect only persisted owner evidence; no Delivered, Implemented or Completed claim is inferred.

## 5. Carried Proposal Notes

Sections of the proposal that did not map to a spec section. Trim or promote them while drafting; they are not contracts.

### 2. Technical Spike Questions

- **Q1**: Which saved, applied, publication-pending and delivery-pending states can existing owner receipts expose, and where is a read-model extension needed?
- **Q2**: Which next actions are valid for ordinary answers, proposal decisions, worker answers and integration authority without treating them as interchangeable?
- **Q3**: How should unknown outcomes, changed heads, later pauses and replayed requests appear while preserving stable mutation identities?

### 3. Proposed Design & Impact

#### Alternatives and decision

| Option | Benefit | Cost and risk |
| --- | --- | --- |
| A: use existing question/attempt/native history views only | No API extension | Ordinary resume receipts are not public; native history caps at 100 and cannot reliably recover a specific lost response. |
| B: read-only owner request outcome plus persistent owner UI, recommended | Exact recovery with existing owner records; preserves authority boundaries | Typed read query and request-intent state in UI; incomplete evidence remains unknown. |
| C: independent continuation ledger or controller | Uniform state machine | Duplicates owner truth and introduces synchronization and authorization drift. |

Choose B. `ADR-decision-continuation-outcomes` records this cross-feature decision. This adds no mutation controller, persistence table or inbox projection.

#### Owner outcome read contract

Add authenticated `GET /api/v1/pipeline-runs/{run_id}/decision-outcomes/{request_id}` with required `operation` discriminator: `question`, `answer`, or `resume`. The discriminator chooses the existing owner namespace; identical UUIDs across namespaces never alias. The caller supplies no authoritative actor. Apply the same run/project visibility and history policy as existing decision reads. Missing/inaccessible runs return 404; invalid operation/UUID returns 422. A missing request on an accessible run returns 200 with `record_state: unknown`, never definite failure. The endpoint performs no repository/provider/network call or mutation and returns no request digest or credentials.

Return a typed response with the requested operation/request ID and run ID; `record_state` (`unknown` or `recorded`); current run revision/state and read observation time; and nullable owner evidence: question/answer IDs, applied attempt ID, execution attempt state, delivery state/time, native request/answer channel, publication state/candidate head, resolved envelope evidence, inspected head/digest and current authority/hold. Include only fields supported by the selected owner's persisted records. No generic `completed` flag or action-authority booleans are introduced. Missing/unsupported facts are null with a reason, distinct from known pending or failed evidence. Never infer delivery from attempt preparation, publication from HTTP success, or current approval from a historical receipt.

Query existing question/answer rows and `RunResumeReceipt` by exact request ID and run ownership. Correlate the receipt's existing execution attempt and delivery records; use a consistent database transaction for the response. Do not scan the capped native history list. For worker answers, extend existing owner inspection to retain validated answer-envelope file/identity, `answers_to`, answered question ID, workflow/segment and inspected head alongside the existing native evidence. Current `evidence.reports` omits answer envelopes; add a bounded owner evidence extractor rather than infer resolution from request disappearance. Correlate that exact evidence to the receipt/decision record. Unrelated envelopes, wrong questions/workflows, malformed links and mere request disappearance do not prove publication; retain publication pending or unknown according to available evidence. Refresh replaces the inspection basis under the predecessor CAS and does not grant authority. Delivery/publication failure labels require their respective recorded failure evidence. An ended run keeps its retained outcome visible while its records exist; run retention remains unchanged.

#### Explicit continuation and unknown outcomes

The selected owner review remains open after mutation and shows the recorded outcome separately from the current run. Reopening the same run and question/request can reconstruct durable evidence. Save answer never selects or applies an answer automatically. Resume with selected answer requires an explicit saved-answer selection, current revision, matching question/head and existing owner guards. Native Hub clarification follows native control, not ordinary resume semantics. Native worker answer recording remains publication pending until matching envelope resolution is observed. Proposal acceptance publication does not imply handoff, integration approval or merge. Integration authority recorded does not imply workflow completion, delivery or PR merge.

Retain the exact endpoint, owner request ID, actor-bound submission intent and immutable payload for every unresolved operation in the active run-review session. Preserve them through read refresh and temporary dialog close/reopen; never derive a new resume ID from the refreshed revision after an uncertain response. Do not persist answer text/payload in browser durable storage. A browser reload loses unacknowledged in-memory intent; the UI explains that the prior unacknowledged intent is unavailable and recovery is read-only from durable owner history. The unresolved replacement-submission guard applies only while the in-memory intent exists; after full reload, new explicitly reviewed operations rely on existing owner revision/head/authority guards, and the UI makes no recovered-intent guarantee. Existing saved answers/native history provide links to their recorded request outcomes; no promise of automatic recovery for a never-recorded request after reload is made.

After a timeout/lost response, show Outcome unknown and Check outcome. A successful mutation response followed by failed refresh remains recorded-with-refresh-error, not mutation failure. Read errors and missing receipts stay unknown. Permit an explicit Retry same request only using the retained original endpoint and complete payload; unchanged owner replay guards remain authoritative. No background retry, new request ID, changed note, alternate answer or generic native resume is substituted. This permits ordinary save replay's existing refreshed-revision semantics only after an acknowledged save ends the prior intent; uncertain save retry still retains its original payload.

If current head/generation/binding/authority differs, keep the historical outcome visible and disable replay-as-continuation. Use the predecessor's exact-subject inspection/CAS to review a fresh basis before any new action; do not silently rebind the old selection. For uncertain native proposal publication, expose the existing owner reconciliation route explicitly and explain its possible inspection/continuation effect; it is not Check outcome and cannot grant authority or override later stops. The workflow panel exposes Reconcile publication through the parent recovery control. After refreshed review, an explicit submission uses the existing native resume/recovery route with its own stable request ID and current expected revision; it does not reuse or alter the original proposal decision payload. Explain possible continuation before submission, retain that recovery intent on uncertainty, and keep it unavailable for ended work. A prior successful receipt can be replayed only as its owner permits; the current paused/revoked/canceled state remains authoritative. No automatic dispatch retry is added; delivery recovery routes to existing run controls.

#### Candidate acceptance examples and verification

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

#### Non-goals

- **Scope Excluded**: implicit application, automatic approval, generic resume as native authority, batch approval, new authority ledgers, inbox projection/age/pagination implementation, browser durable storage of decision text, and automatic delivery recovery.
- **Scope Excluded**: provider/SDK/Jules decision support, operations, pilot/deployment/live verification, monitoring and CI changes.

#### Planning assumptions and dependency revalidation

The user authorized routine design choices and requested separate UX review. B and the owner-modal arrangement are assumptions within that scope; no business choice blocks this turn. High Development effort remains appropriate because replay, external publication and authority disclosure span persisted owner boundaries.

`SPEC-operator-decision-inbox` is completed and landed at base 7035c33. Its exact-subject CAS and native answer extractor are reused. Its exact-subject selection, first-observed native age, refreshed inspection and CAS persistence are provisional prerequisites, reused without duplication. Before Development or handoff, compare the landed predecessor's exact completed spec and implementation with this bundle, replace the dependency anchor through the normal process, and revise any mismatched fields/routes/UI boundaries. Recheck touched owner tests, generated types and active branch overlap; do not treat this branch's checks as evidence for the eventual landed head.

### 4. Lifecycle & Retirement Criteria

User plan-intent authorizes this high-effort Planning turn. ORDER OVERRIDE: Planning may precede completion of `SPEC-operator-decision-inbox`; this exception authorizes Planning only. The accepted inbox design is a provisional dependency, not implemented evidence. No plan-accept or Development handoff authority is supplied. Planning resolves the spike
questions, evaluates the recommended design and drafts affected interactions
before code. The milestone frames the theme without binding the final scope.

The direct prerequisite is `SPEC-operator-decision-inbox`. It supplies the shared foundation described above. Eligibility requires its exact completed spec anchor after handoff; update the edge through the normal handoff reference process.

Acceptance and Development handoff follow `sdd-proposal`. Rejection retains
the decision and reason through the proposal lifecycle. This proposal is complete
only through a verified accepted implementation, not from creating this draft.


## Screens

### Candidates

- **A — owner review with persistent outcome region, recommended**: retain the selected subject and show its recorded result, current run state and explicit next action beside owner controls. This preserves review context after a row leaves the inbox.
- **B — separate continuation screen**: gives follow-through its own primary region but adds navigation and duplicates owner context.
- **C — transient success notice and run link**: costs less but loses the saved/applied/publication distinction when a response is lost or the dialog reopens.

A is the within-scope assumption. These drafts amend existing elements; existing controls and style remain governed by their owning UX documents. The predecessor owns inbox layout, exact-subject Review, waiting age, and native inspection/CAS. No continuation action is added to discovery rows.

### UX-run-decisions — Run decisions (modal amendment)

- **Use cases**: `UC-resolve-run-question`, `UC-complete-sdd-workflow`, `UC-decide-sdd-proposal`.
- **Capabilities**: `CAP-PR-operator-decisions`, `CAP-SDD-workflow-control`, `CAP-SDD-native-delivery`.
- **Purpose**: Follow one exact question/request through its recorded outcome and choose the next owner action. Facts: project/run, question/request identity, selected answer, inspected head/revision, recorded request and current run state. Other decisions stay in history or the existing native panels.

#### Content

The selected decision and its outcome are the primary region. History is secondary. The outcome remains visible after the question leaves the pending list and is reachable by its run/question or request identity on reopening.

- PR run: current state, last loaded time and Open run / Inspect pull request.
- Run question: exact question, saved answers, explicit selected answer and Save answer.
- Recorded outcome: Saved, Applied to attempt, delivery evidence or Outcome unknown; saved answer text remains inspectable separately from the composer.
- Native SDD activity: the exact workflow panel or integration panel below.
- Recovery: Check outcome; Retry same request only when eligible; Review current context after change.
- Close: returns focus to originating inbox row or nearest remaining neighbor, preserving filters and page.

#### States

- **loading**: Wait for current owner reads; decision controls disabled; Close remains available.
- **empty**: Subject unavailable/resolved without retained accessible detail; explain and offer Open run or Close.
- **saved**: Answer saved; run remains stopped. Show Resume with selected answer only for an eligible explicitly selected saved answer. No default selection or application follows Save.
- **applied**: Applied to attempt identifies the existing attempt; show delivery independently and Open run. Later pause is shown as current state and is not overridden.
- **uncertain**: Outcome unknown identifies the original operation; editing/replacement submissions disabled while the in-memory original intent is retained. After a full reload it cannot be reconstructed automatically; explain the limit and use owner history/current review, without claiming a recovered retry guard. Offer Check outcome, eligible Retry same request, Open run and Close. A read error or absent receipt does not prove failure.
- **changed**: Show changed context and retained answer separately; disable old continuation. Offer Review current context; stale ordinary answers require existing dismissal/new-question flow rather than application to the changed head.
- **acknowledged-refresh-error**: Keep the acknowledged saved/applied/recorded outcome and original identity visible with Refresh failed and Retry read. Disable new continuation until current context reloads; do not replace the mutation or relabel its acknowledged result unknown.
- **error**: A definitive validation failure shows its owner message and offers correction after review; no success is inferred.
- **terminal**: Retained result is readable; no continuation is offered for ended work.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save answer | `UC-resolve-run-question` 2 | populated | saved | | `CAP-PR-operator-decisions` | Saved answer ID/text shown; execution remains stopped. |
| Select saved answer / Resume with selected answer | `UC-resolve-run-question` 4, 5, `UC-complete-sdd-workflow` 3d | saved | applied, uncertain, changed | | `CAP-PR-operator-decisions` | Selection is explicit; existing owner checks apply; recorded attempt is distinct from delivery. |
| Check outcome | `UC-resolve-run-question` 2b, 4d, `UC-complete-sdd-workflow` *b, `UC-decide-sdd-proposal` 3d | uncertain | saved, applied, uncertain, changed | | `CAP-PR-operator-decisions` | Reads original request outcome and current state; never starts work. |
| Retry same request | `UC-resolve-run-question` 2b, 4d, `UC-complete-sdd-workflow` *b, `UC-decide-sdd-proposal` 3d | uncertain | saved, uncertain, applied, changed | | `CAP-PR-operator-decisions`, `CAP-SDD-workflow-control` | Original immutable payload and owner request ID replay; successful ordinary save replay returns its saved answer without applying it; no automatic replay. |
| Review current context | `UC-resolve-run-question` 4b, `UC-complete-sdd-workflow` 4e, `UC-decide-sdd-proposal` 3b | changed | loading | | `CAP-SDD-workflow-control` | Predecessor inspection refreshes exact subject; nothing is submitted. |
| Open run / Inspect pull request | `UC-resolve-run-question` 5, 5a, `UC-complete-sdd-workflow` 5, `UC-decide-sdd-proposal` 6 | applied, saved, uncertain, terminal | populated | end | `CAP-PR-operator-decisions` | Bound run or pull request opens with retained outcome accessible on return. |
| Close | global: return from decision review | all | populated | close | | Origin and focus restored. |

### UX-sdd-workflow-request — Workflow request (panel amendment)

- **Use cases**: `UC-complete-sdd-workflow`, `UC-decide-sdd-proposal`.
- **Capabilities**: `CAP-SDD-workflow-control`, `CAP-SDD-native-delivery`.
- **Purpose**: See whether the selected native decision is recorded, published or still waiting. Facts: exact request, answer channel, reviewed head, retained request identity and current publication evidence. Execution history stays with Open run.

#### Content

The exact request outcome is primary. Parent `UX-run-decisions` supplies context and exit. Worker answers say Answer recorded — publication pending until a matching answer envelope resolves the question. Proposal decisions distinguish preparation, publication uncertain, published, and published without current authority. Other workflow record/given channels retain their own effects. Decline/defer retain the open request.

#### States

- **populated**: Existing exact-request controls remain; labels name the channel effect.
- **recorded**: Pending worker publication disables duplicate answer controls. Show View publication progress and Check outcome.
- **published**: Show matched publication evidence and current request/run separately; no automatic handoff or integration authority follows proposal acceptance.
- **uncertain**: Show Outcome unknown and immutable request; Check outcome or eligible Retry same request. For uncertain proposal publication, show Reconcile publication with an explanation that owner inspection may continue the run, preserves all stop/authority fences, and is distinct from reading outcome.
- **changed**: Require refreshed review before any replacement answer; historical outcome stays visible.
- **held/error/empty/loading**: Explain the hold, owner error, absence or loading; Check outcome/Review current context and parent Close remain available. No unavailable evidence is called published.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Record worker answer | `UC-complete-sdd-workflow` 3b | populated | recorded, uncertain | | `CAP-SDD-workflow-control` | Answer retained; question remains open until envelope publication. |
| Confirm workflow choice / Approve / Decline / Defer | `UC-complete-sdd-workflow` 3c | populated | recorded, uncertain | | `CAP-SDD-workflow-control` | Owner result shown; declined/deferred request stays open. |
| Accept / Reject proposal | `UC-decide-sdd-proposal` 2, 2a | populated | recorded, published, uncertain | | `CAP-SDD-native-delivery` | Existing head confirmation/rejection reason remain; publication and merge are separate. |
| Check outcome / eligible Retry same request | `UC-complete-sdd-workflow` *b, `UC-decide-sdd-proposal` 3d, 5b, 6a, 6b | recorded, uncertain | recorded, published, uncertain, changed | | `CAP-SDD-native-delivery` | Read first; explicit replay uses original input; publication after stop never revives authority. |
| Reconcile publication | `UC-decide-sdd-proposal` 5b, 6a, 6b | uncertain | recorded, published, uncertain, changed | `UX-run-decisions` | `CAP-SDD-native-delivery` | Opens the parent recovery control with current review required; explicit submission may inspect/continue, never approve or undo a later stop. |
| View publication progress / Back to review | `UC-complete-sdd-workflow` 3b, `UC-decide-sdd-proposal` 6 | all | populated | `UX-run-decisions` | `CAP-SDD-workflow-control` | Parent review retains the exact request and accessible run link. |

### UX-sdd-run — Native execution (panel amendment)

- **Use cases**: `UC-complete-sdd-workflow`, `UC-decide-sdd-proposal`.
- **Capabilities**: `CAP-SDD-workflow-control`, `CAP-SDD-native-delivery`.
- **Purpose**: Follow retained integration authority and current execution independently. Facts: approved head/basis, current head, hold/revocation, current run and recorded outcome. Reports stay in existing disclosures.

#### Content

Current integration outcome is primary. Parent `UX-run-decisions` owns close/navigation. Show Authority recorded independently of workflow integration, PR delivery and merge. Revocation/hold/later pause take precedence for available actions. A successful API response does not become Delivered or Completed.

#### States

- **populated**: Current basis and existing approval/revise/revoke/reject controls are explicit.
- **recorded**: Authority recorded; show current waiting/running state and Open run. No second approval action while the basis remains authorized.
- **uncertain**: Check outcome; eligible exact replay is distinct from new approval.
- **changed/held**: Show changed head/hold/revocation and require reviewed current basis. Resume after inspection is labelled as inspection/continuation and never as approval.
- **terminal/error/empty/loading**: Explain terminal result, read failure, missing evidence or loading; offer parent Close/Open run/Retry read where applicable; approval stays disabled without current evidence.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Approve / Request changes / Withdraw approval / Stop run | `UC-complete-sdd-workflow` 4, 4b, 4c, 4d | populated, recorded | recorded, held, uncertain | | `CAP-SDD-workflow-control` | Existing reason/confirmation requirements retained; resulting authority and run state shown separately. |
| Check outcome / eligible Retry same request | `UC-complete-sdd-workflow` *b | uncertain | recorded, held, changed, uncertain | | `CAP-SDD-workflow-control` | Original receipt replay cannot undo a later pause or revocation. |
| Review current context | `UC-complete-sdd-workflow` 4e | changed, held | loading | `UX-run-decisions` | `CAP-SDD-workflow-control` | Fresh inspection; no approval granted. |
| Open run / Back to review | `UC-complete-sdd-workflow` 5, `UC-decide-sdd-proposal` 6 | all | populated | `UX-run-decisions` | `CAP-SDD-workflow-control` | Parent retains run link, exact context and close exit. |

### Use case and register amendments

Retain each use case's main flow and extensions. `UC-resolve-run-question` step 2 shows saved feedback, step 3 retains the saved result, step 4 explicitly selects the saved answer, and step 5 follows the existing attempt/run. Its 2b/4d recovery names the original request and treats missing receipt as unknown; 4b requires changed-head dismissal/new question before another application. `UC-complete-sdd-workflow` 3b shows publication pending, 3c preserves channel semantics, 3d separates applied from delivered, 4/4b/4c/4d shows authority, and *b names exact-request replay and later stop precedence. `UC-decide-sdd-proposal` 3d/5b/6a/6b distinguish recorded intent, published candidate and currently valid authority. All amended steps cite their owner UX above.

| Object | Role | Added representations | Added calls to action |
| --- | --- | --- | --- |
| Run question | Operator | Saved/applied answer and exact selected answer; retained outcome | Check outcome, Resume with selected answer |
| Execution attempt | Operator | Prepared application with independent delivery evidence | Open run, inspect attempt |
| Native SDD activity | Operator | Recorded/publication-pending/published/uncertain outcome and current authority | Check outcome, Retry same request, View publication progress, Reconcile publication, Review current context |
| PR run | Operator | Current pause/terminal state beside historical outcome | Open run |

Use existing style tokens and modal/panel hierarchy. No new domain object, screen or inline inbox mutation is introduced. No prototype or browser verification is claimed.

### UX review fold

Separate round 1 walked all three use cases. Its acknowledged-refresh-error, discoverable publication reconciliation, and ordinary saved-replay destination findings are folded above. Original findings remain in ux-review-01 for the Host at plan-accept; Development verifies retained screens and closes them. No browser/prototype result is claimed.
