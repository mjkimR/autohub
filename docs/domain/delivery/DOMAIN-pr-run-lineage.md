---
id: DOMAIN-pr-run-lineage
title: "PR run lineage"
status: active
area: delivery
summary: "Separates the records that belong to a PR run (epoch, attempts, deliveries, replies, questions, answers and resume receipts) from the Work Items, Provider sessions and SDD activity claims that only refer to it, and shows what each keeps when the Run is retired."
related_capabilities: [CAP-PR-pull-request-delivery, CAP-PR-agent-dispatch, CAP-PR-operator-decisions, CAP-EXEC-scheduling-maintenance, CAP-AGENT-provider-sessions, CAP-SDD-native-delivery, CAP-WORK-work-plan-execution]
related_usecases: [UC-deliver-pull-request, UC-resolve-run-question, UC-execute-work-plan]
related_domains: [DOMAIN-work-item-lineage]
---

# [DOMAIN-pr-run-lineage] PR run lineage

Readers confuse the records that make up a PR run with the records that point at it. An epoch, an Execution
attempt and a delivery are all "another try", but at different granularity; a Work Item, a Provider session and an
SDD activity claim each show a Run as their execution, yet none of them is part of it. The difference decides which
repair budget a try consumes and which history survives once the Run's detail is retired. Terms are defined in the
[glossary](../../steering/glossary.md).

## Relationship overview

A PR run delivers one PR of one project; while it is nonterminal it is that PR's only active owner. Everything
below the Run in the first group is created by the Run's own progression and has no meaning without it.

| Concept or relationship | Distinction | Authoritative owner |
| --- | --- | --- |
| Epoch | The Run's repair window. It starts at 1 and advances only when an operator resume sends new work; a resume that adopts an already pushed head, an automatic repair and a Work Item recovery stay in the current epoch. CI-fix and conflict-fix limits count per epoch. | `CAP-PR-pull-request-delivery` §4 Catalog and advancement selection and §3 rules 14 and 23–24 |
| Execution attempt | One immutable request of kind `implementation`, `ci-fix` or `conflict-fix`, numbered within the Run and tagged with its epoch. A repair is a new attempt; a deliberate resume that sends work is a new attempt in a new epoch. | `CAP-PR-pull-request-delivery` §4 Public HTTP surface |
| Delivery | One numbered attempt to post that attempt's request as a PR mention. A silent, quota or recovery retry is another delivery of the same attempt, not a new request, and the catalog ledger counts it once. | `CAP-PR-agent-dispatch` §1 and §3 rules 7, 11 and 13 |
| Reply | A trusted provider comment observed for one attempt. | `CAP-PR-agent-dispatch` §2 |
| Run question and answer | A question is bound to the Run, the current PR head and optionally the attempt that raised it; at most one is pending per Run. Answers belong to the question; saving one creates no attempt. Applying one records the new attempt it was prepared into. | `CAP-PR-operator-decisions` §3 rules 1, 8 and 11 and §4 Records and transitions |
| Resume receipt | The identity of one explicit resume request on the Run and the attempt it prepared, kept so a replay returns the current Run instead of repeating the resume. | `CAP-PR-operator-decisions` §4 Records and transitions |
| Work Item → Run | The Item records the one Run that delivers its PR. The Item's specification, outcome and merge evidence belong to the Item, which also protects an unresolved Run from retirement. | `CAP-WORK-work-plan-execution` §3 rules 19 and 25 and §4 Outbound mirrors and retained results |
| Provider session → Run | A completed Jules task session records the Run that adopted its PR, or the existing Run it was linked to. The session and its report belong to the session. | `CAP-AGENT-provider-sessions` §3 rules 17–20 |
| SDD activity claim → Run | The claim reserves one unit/activity request and records the Run bound to its publication. An unsettled claim keeps its Run from retirement. | `CAP-SDD-native-delivery` §4; `CAP-EXEC-scheduling-maintenance` §6 |
| Related origins | The Run read projects whichever of the three referrers are still retained. They are current relationships, not immutable provenance of how the Run was first entered: retention on either side can remove them, and an unproven category reads as `unknown`. | `CAP-PR-pull-request-delivery` §3 rules 27–28 and §4 Retained origin read |

The first six rows nest: Run → epoch → attempt → delivery and reply, with questions, answers and resume receipts
hanging from the Run and pointing at attempts. The last four rows run the other way: an owner outside the Run keeps
a reference to it, and that owner's lifetime is independent of the Run's.

## Retirement walkthrough

A Work Plan Item admits Run 1 for PR #42. The first implementation attempt is delivered twice because the first
mention got no push before the silent watchdog; both deliveries belong to attempt 1. CI fails, so attempt 2 is a
`ci-fix` in epoch 1. The agent asks a question; the operator saves an answer, and an explicit resume prepares
attempt 3 in epoch 2 carrying that answer, recorded on the answer and in a resume receipt. PR #42 then merges and the
Item succeeds with its merge SHA.

When maintenance later retires Run 1, its detail and resume surface disappear together with the nested group:
the three attempts, their deliveries and replies, the question, the answer and the resume receipt. The Item keeps
its repository, target, PR URL, merge SHA, execution identity and completion time, and records when its Run link was retired. Had a Jules
session adopted PR #42 instead, the session would keep its report and PR URL and its retirement marker would stop
it from adopting the PR again. Had the Run come from an SDD activity whose claim was still unsettled, the Run would
not have been retired at all. PR #42 and its branch on GitHub are untouched in every case.

The schema expresses the same split: attempts, questions, resume receipts and rebuildable decision entries are
deleted with their Run (`ON DELETE CASCADE`), and deliveries, replies and answers with their attempt or question;
the Work Item and Provider session references are cleared, and an SDD claim reference blocks deletion until the claim settles
(`modules/hub/app/features/project_management/pipeline_runs/models.py`,
`modules/hub/app/features/execution/tasks/domains/maintenance/history.py`).

## Authority boundary

The retention ages, per-pass limits and lease guard belong to `CAP-EXEC-scheduling-maintenance` §3 rule 12 and §4.
Which PR state and CI evidence authorize a merge, and which budgets block a Run, remain with
`CAP-PR-pull-request-delivery` and `CAP-PR-ci-observation`; this document only places them on the epoch or attempt
they count against.

## Update triggers

- `PipelineRun`, `ExecutionAttempt`, `ExecutionDelivery`, `ExecutionReply`, `RunQuestion`, `RunAnswer`,
  `RunResumeReceipt` or `DecisionEntry` change their parent reference or delete behavior.
- `PipelineRunControl.resume_run` or Work Item terminal recovery changes when `epoch` advances.
- `CAP-PR-pull-request-delivery` §3 rules 23–28 or §4 Retained origin read change what recovery keeps or what a Run
  read projects.
- `CAP-EXEC-scheduling-maintenance` §3 rule 12, §4 or §6 change which Runs are retired or what
  retirement keeps; `CAP-WORK-work-plan-execution` rules 19 and 25 or `CAP-AGENT-provider-sessions` adoption rules
  change a referrer's retained evidence.
