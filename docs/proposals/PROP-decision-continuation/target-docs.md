---
id: PROP-decision-continuation-target
title: Living Spec targets for PROP-decision-continuation
summary: "Candidate contract and interface updates for follow decisions through explicit continuation."
status: draft
proposal: PROP-decision-continuation
created_at: 2026-11-05
targets:
  - file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
  - file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
  - file: docs/usecases/delivery/UC-resolve-run-question.md
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
  - file: docs/usecases/sdd/UC-decide-sdd-proposal.md
  - file: docs/ux/delivery/UX-run-decisions.md
  - file: docs/ux/sdd/UX-sdd-workflow-request.md
  - file: docs/ux/sdd/UX-sdd-run.md
  - file: docs/steering/ux-objects.md
---

# [Blueprint] PROP-decision-continuation: Living Spec targets

This draft records candidate reconciliation targets. It does not change the
implemented guarantees; Planning settles the final scope and screen drafts.

## 1. System Capabilities Plan

Extend outcome disclosure and continuation navigation while preserving the save/apply and decision/publication guarantees in the existing owning capabilities.

## 2. Use Cases and Interface Plan

Extend `UC-resolve-run-question` and `UC-complete-sdd-workflow` with post-decision continuation, uncertainty and stale-context examples. Draft the changed state/action regions of `UX-run-decisions`, `UX-sdd-workflow-request` and `UX-sdd-run` during Planning.

Update the existing Work Item, SDD unit, PR run or Run question representations
in `docs/steering/ux-objects.md` where the accepted interface adds actions.
Register any distinct object only after checking the glossary during Planning.

## 3. Architecture and Decision Impact

No replacement approval or execution controller is proposed. Planning identifies the minimum owner read-model changes needed for truthful outcome disclosure.

## 4. Development Conventions and Governance

No devkit workflow, governance rule or toolchain change is proposed. Regenerate
the typed UI client if accepted API changes require it. Use existing API access
and owner-specific revision checks.

## 5. Before and After

Before: a completed save or decision can require locating a separate continuation action. After: the reviewed context shows the actual outcome and its explicit owner-authorized next step.

## 6. Screens

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
- **uncertain**: Outcome unknown identifies the original operation; editing/replacement submissions disabled. Offer Check outcome, eligible Retry same request, Open run and Close. A read error or absent receipt does not prove failure.
- **changed**: Show changed context and retained answer separately; disable old continuation. Offer Review current context; stale ordinary answers require existing dismissal/new-question flow rather than application to the changed head.
- **error**: A definitive validation failure shows its owner message and offers correction after review; no success is inferred.
- **terminal**: Retained result is readable; no continuation is offered for ended work.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save answer | `UC-resolve-run-question` 2 | populated | saved | | `CAP-PR-operator-decisions` | Saved answer ID/text shown; execution remains stopped. |
| Select saved answer / Resume with selected answer | `UC-resolve-run-question` 3, `UC-complete-sdd-workflow` 3d | saved | applied, uncertain, changed | | `CAP-PR-operator-decisions` | Selection is explicit; existing owner checks apply; recorded attempt is distinct from delivery. |
| Check outcome | `UC-resolve-run-question` 3a, `UC-complete-sdd-workflow` *b, `UC-decide-sdd-proposal` 3d | uncertain | saved, applied, uncertain, changed | | `CAP-PR-operator-decisions` | Reads original request outcome and current state; never starts work. |
| Retry same request | `UC-resolve-run-question` 3a, `UC-complete-sdd-workflow` *b, `UC-decide-sdd-proposal` 3d | uncertain | uncertain, applied, changed | | `CAP-SDD-workflow-control` | Original immutable payload and owner request ID replay; no automatic replay. |
| Review current context | `UC-resolve-run-question` 3b, `UC-complete-sdd-workflow` 4e, `UC-decide-sdd-proposal` 3b | changed | loading | | `CAP-SDD-workflow-control` | Predecessor inspection refreshes exact subject; nothing is submitted. |
| Open run / Inspect pull request | `UC-resolve-run-question` 4, `UC-complete-sdd-workflow` 5, `UC-decide-sdd-proposal` 6 | applied, saved, uncertain, terminal | populated | end | `CAP-PR-operator-decisions` | Bound run or pull request opens with retained outcome accessible on return. |
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
- **uncertain**: Show Outcome unknown and immutable request; Check outcome or eligible Retry same request.
- **changed**: Require refreshed review before any replacement answer; historical outcome stays visible.
- **held/error/empty/loading**: Explain the hold, owner error, absence or loading; Check outcome/Review current context and parent Close remain available. No unavailable evidence is called published.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Record worker answer | `UC-complete-sdd-workflow` 3b | populated | recorded, uncertain | | `CAP-SDD-workflow-control` | Answer retained; question remains open until envelope publication. |
| Confirm workflow choice / Approve / Decline / Defer | `UC-complete-sdd-workflow` 3c | populated | recorded, uncertain | | `CAP-SDD-workflow-control` | Owner result shown; declined/deferred request stays open. |
| Accept / Reject proposal | `UC-decide-sdd-proposal` 2, 2a | populated | recorded, published, uncertain | | `CAP-SDD-native-delivery` | Existing head confirmation/rejection reason remain; publication and merge are separate. |
| Check outcome / eligible Retry same request | `UC-complete-sdd-workflow` *b, `UC-decide-sdd-proposal` 3d, 5b, 6a, 6b | recorded, uncertain | recorded, published, uncertain, changed | | `CAP-SDD-native-delivery` | Read first; explicit replay uses original input; publication after stop never revives authority. |
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

Retain each use case's main flow and extensions. `UC-resolve-run-question` step 2 shows saved feedback, step 3 explicitly selects the saved answer, step 4 follows the existing attempt/run. Its 3a recovery names the original request and treats missing receipt as unknown; 3b requires changed-head dismissal/new question before another application. `UC-complete-sdd-workflow` 3b shows publication pending, 3c preserves channel semantics, 3d separates applied from delivered, 4/4b/4c/4d shows authority, and *b names exact-request replay and later stop precedence. `UC-decide-sdd-proposal` 3d/5b/6a/6b distinguish recorded intent, published candidate and currently valid authority. All amended steps cite their owner UX above.

| Object | Role | Added representations | Added calls to action |
| --- | --- | --- | --- |
| Run question | Operator | Saved/applied answer and exact selected answer; retained outcome | Check outcome, Resume with selected answer |
| Execution attempt | Operator | Prepared application with independent delivery evidence | Open run, inspect attempt |
| Native SDD activity | Operator | Recorded/publication-pending/published/uncertain outcome and current authority | Check outcome, Retry same request, View publication progress, Review current context |
| PR run | Operator | Current pause/terminal state beside historical outcome | Open run |

Use existing style tokens and modal/panel hierarchy. No new domain object, screen or inline inbox mutation is introduced. No prototype or browser verification is claimed.
