---
id: DOMAIN-work-item-lineage
title: "Work Item lineage"
status: active
area: work-plans
summary: "Distinguishes Work Item recovery, replacement registration, replacement links and edge acceptance by the identity each keeps and the dependency each can release; behavior stays with the Work Plan and PR delivery capabilities."
related_capabilities: [CAP-WORK-work-plan-execution, CAP-PR-pull-request-delivery, CAP-PR-owed-items]
related_usecases: [UC-execute-work-plan, UC-reuse-work-plan-templates]
related_domains: [DOMAIN-pr-run-lineage]
---

# [DOMAIN-work-item-lineage] Work Item lineage

When a Work Item stops unsuccessfully, readers confuse four ways of continuing its work: recovering the original
Item, registering replacement work, linking that replacement to the original and accepting the replacement's merge
for one dependent edge. Each keeps a different identity, and only one of them can release a waiting dependent
without the original succeeding. `ADR-work-item-recovery-lineage` and `ADR-work-item-replacement-evidence` record
why the lines are drawn this way; terms are defined in the [glossary](../../steering/glossary.md).

## Relationship overview

A Work Item belongs to exactly one Work Plan. Item dependencies are local to that Plan and wait for a `succeeded`
predecessor; Plan dependencies connect Plans in the same project and wait for a `completed` Plan. Neither kind of
edge crosses into the other, so a dependency on another Plan's Item does not exist. An admitted Item links to at
most one PR run; the Item's outcome reflects that Run but is retained by the Item, as `DOMAIN-pr-run-lineage`
explains for Run retirement.

| Concept or relationship | Distinction | Authoritative owner |
| --- | --- | --- |
| Item dependency release | Released only by the predecessor's confirmed merge to its original target, or by a live accepted replacement for that exact edge. A missing Run or a different-target merge releases nothing. | `CAP-WORK-work-plan-execution` §3 rules 9 and 38 |
| Plan dependency release | Waits for the predecessor Plan to be `completed`; replacement evidence never satisfies it, and a revoked Plan never completes. | `CAP-WORK-work-plan-execution` §4 Lifecycle and ownership; §3 rule 28 |
| Work Item recovery | Continues the same Item and, when one is linked, the same Run with its epoch, attempt numbering and delivery history. It adds an immutable recovery record; it creates neither a new Item nor a new Run. At most one recovery is pending per Item. | `CAP-WORK-work-plan-execution` §3 rules 29–36 and §4 Explicit Work Item recovery; `CAP-PR-pull-request-delivery` §3 rules 23–26 |
| Replacement registration | Ordinary new work: another Plan with its own registration `request_id`, Items, Runs and completion. Registration identity stays on its own Plan row. Its success is not evidence for the original graph, and independently enrolling a PR is not either. | `CAP-WORK-work-plan-execution` §3 rules 2 and 28 |
| Replacement link | A retained relation from one stopped original Item to one distinct replacement Item. An original has at most one active link; a replacement Item is bound to one link for its retained lifetime, and the two endpoint roles never switch. Withdrawing an unconsumed link frees the original for a distinct, never-linked replacement. Linking alone releases nothing and can precede the replacement's success. | `CAP-WORK-work-plan-execution` §3 rules 37, 39 and 44; §4 Explicit replacement evidence |
| Replacement edge acceptance | An operator's review that the linked replacement's confirmed merge satisfies one existing local edge from the original to one dependent. It binds both specification digests and the replacement's own merge evidence, satisfies only that edge and leaves every other admission gate in place. | `CAP-WORK-work-plan-execution` §3 rules 38, 40 and 42 |
| Acceptance consumption | Admission of the dependent consumes the acceptance. Before consumption the acceptance or the whole link can be withdrawn and accepted again; afterwards it is irreversible admission history. | `CAP-WORK-work-plan-execution` §3 rules 40–41 |
| Original outcome | Never changes through replacement: the original Item stays `preparation_failed`, `failed`, `canceled` or `revoked`, its Plan stays uncompleted and its PR ownership is unchanged. Only the original's own recovery can make it succeed. | `CAP-WORK-work-plan-execution` §3 rule 37; `UC-execute-work-plan` §4 Postconditions |

Recovery and replacement therefore answer different questions. Recovery asks whether the same specification on
the same PR can still finish; replacement asks whether different work already merged elsewhere is good enough for a
particular dependent. Hub validates identities and merge facts for both; only the operator judges semantic
equivalence of a replacement.

## Failed predecessor walkthrough

Plan P holds Item A and Items B and C, each depending on A. A's Run fails, so B and C keep waiting.

- **Recover A.** The operator confirms recovery of unchanged work. Hub keeps Item A and its Run, does not reset the
  epoch or the retained attempt budget, and continues delivery on A's original PR. If A merges to its original
  target, A succeeds and both B and C are released through the ordinary rule.
- **Register replacement work.** The operator registers Plan Q containing Item R, which reuses or rewrites A's
  intent. R merges and Q completes. B and C still wait: Q's completion belongs to Q's own graph.
- **Link A to R.** The operator compares the two specifications and links A to R. B and C still wait; the link
  is evidence of intent, not release. A cannot gain a second active link while this one is live, and R cannot be
  linked to any other original.
- **Accept R for the edge A→B.** With R's confirmed merge retained, the operator accepts it for B only. When B is
  admitted, the acceptance is consumed. C still waits for A, A remains failed and P cannot complete while A is
  unfinished. Any Plan that depends on P keeps waiting.

## Update triggers

- `CAP-WORK-work-plan-execution` §3 rules 9, 28–45 or its §4 Lifecycle, recovery or replacement sections change
  what releases a dependency, what recovery retains or how a replacement link or acceptance is scoped.
- `CAP-PR-pull-request-delivery` §3 rules 23–26 change what terminal recovery keeps on the Run.
- `WorkItem`, `WorkItemRecovery`, `ReplacementLink` or `ReplacementAcceptance` in
  `modules/hub/app/features/project_management/work_plans/` change their uniqueness (one pending recovery per Item,
  one active link per original, one lifetime link per replacement, one live acceptance per edge).
- `UC-execute-work-plan` changes its recovery or replacement extensions or postconditions.
