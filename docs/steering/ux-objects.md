---
title: UX object register
summary: "Read before describing or changing Auto Hub interfaces; maps shared domain objects to the roles, representations and calls to action used by the implemented UI."
---

# UX object register

| Object | Role | Representations | Calls to action |
| --- | --- | --- | --- |
| Account | Administrator | Approval/status row, access-change form, access-event history | Approve, reject, suspend, activate, promote, demote, inspect history |
| Browser session | Operator | Sign-in form, restoration indicator, signed-in application shell | Sign in, use Google sign-in, sign out |
| Machine | Administrator | Scoped identity form, activation row | Create, activate, deactivate, inspect keys |
| Machine key | Administrator | Key table, one-time issued-key notice | Issue, revoke, copy, dismiss |
| Project connection | Operator | Project row, detail header, settings form, connector/catalog selectors | Create, open, edit, enable/disable automation, check connection, inspect repository/runs |
| Connector | Operator | Provider credential row, creation/edit form, project/catalog selector | Register, edit, rotate secret, delete, select |
| AI catalog | Operator | Admission card, concurrency/availability/quota/connector forms | Add, enable/disable, change concurrency, change quota/refresh policy, clear hold, select connector, inspect sessions |
| Provider session | Operator | Collected session row, report disclosure, session/PR/run links | Inspect report, open provider session, inspect PR or admitted run |
| Connection test | Operator | Recipe selector, execution/result card, cleanup review region | Start PR test, Check/continue now, Cancel test, Review cleanup, Confirm review |
| Schedule configuration | Operator | Schedule row, editor, project/agent schedule dialog | Create, edit, enable/disable, delete, request Run now, inspect jobs |
| Schedule job | Operator | Execution-history row, status/error metadata | Search, filter, refresh, inspect outcome |
| Task specification | Operator | Registered-task card, payload-schema disclosure | Search, refresh, inspect schema |
| Work Plan | Operator | Grouped summary card, inline editor, activity/change disclosures | Create, edit draft, submit, pause, resume, revoke, regroup, comment, inspect activity |
| Work Item | Operator | Requirement/dependency row, state, retained run/PR links, recovery disclosure and paged history | Add/edit draft item, set dependencies, inspect specification or linked execution, retry unchanged work, inspect recovery history, refresh/check original request |
| PR run | Operator | Filtered run row, state/lease context, control/decision dialog | Enroll PR, advance, pause, resume, cancel, attach PR, inspect decisions/attempts |
| Execution attempt | Operator | Summary row, request/reply timeline, retained evidence | Open history, inspect request/reply, follow provider/PR evidence |
| Run question | Operator | Pending question, answer editor, decision history | Ask, save answer, select answer for resume, dismiss |
| SDD unit | Operator | Branch document, proposal/readiness row, milestone member/prerequisite row, effort selection | Browse, check readiness, select eligible subset, inspect suggested order, clear selection, start Planning, start Development, inspect execution lineage |
| Native SDD activity | Operator | Workflow stage/request panel, evidence, approval/publication status, decision history | Answer request, approve integration, request revision, revoke approval, reject, reconcile |
| Repository viewer | Operator | Branch selector, tree, file content, unit execution links, milestone selector and captured preview basis | Switch branch, browse file, refresh, preview milestone, open related run/PR |
| Webhook delivery | Operator | Event/outcome row, retained delivery identifiers | Filter noteworthy/status, page, refresh, inspect outcome |
| Notification channel | Operator | Destination card, credential/configuration form, delivery status | Add, edit, enable/disable, send test, delete |
| Operator notice | Operator | Delivery result, last-error or last-sent indicator | Inspect delivery feedback |
| System configuration | Operator | Read-only JSON record card | Refresh, inspect value |

Domain definitions and exclusions belong in [the glossary](glossary.md).
Element content, states and step-linked interactions belong in the
[UX documents](../ux/README.md). Product guarantees remain with their CAPs.
