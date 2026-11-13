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
| Project connection | Operator | Decision inbox row/filter and exact owner subject, Project row, detail header, settings form, connector/catalog selectors | Create, open, edit, enable/disable automation, check connection, inspect repository/runs ; Review exact decision, filter pending work |
| Connector | Operator | Provider credential row, creation/edit form, project/catalog selector | Register, edit, rotate secret, delete, select |
| AI catalog | Operator | Admission card, concurrency/availability/quota/connector forms | Add, enable/disable, change concurrency, change quota/refresh policy, clear hold, select connector, inspect sessions |
| Provider session | Operator | Collected session row, report disclosure, session/PR/run links | Inspect report, open provider session, inspect PR or admitted run |
| Connection test | Operator | Recipe selector, execution/result card, cleanup review region | Start PR test, Check/continue now, Cancel test, Review cleanup, Confirm review |
| Schedule configuration | Operator | Schedule row, editor, project-owned schedule list (Automation tab), CI observation dialog, agent schedule region | Create, edit, enable/disable, delete, request Run now, inspect jobs |
| Schedule job | Operator | Execution-history row, status/error metadata | Search, filter, refresh, inspect outcome |
| Task specification | Operator | Registered-task card, payload-schema disclosure | Search, refresh, inspect schema |
| Work Plan | Operator | Grouped summary card, inline editor, activity/change disclosures | Create, edit draft, submit, pause, resume, revoke, regroup, comment, inspect activity |
| Work Plan template | Operator | Name/ID/revision/item-count list, saved definition editor, immutable-source editable registration preview, original request outcome | Save definition, Edit template, Delete template, Use template, Review registration, Check original request, Retry same request |
| Work Item | Operator | Requirement/dependency row, state, retained run/PR links, recovery disclosure, replacement comparison and paged history | Add/edit draft item, set dependencies, inspect specification or linked execution, retry unchanged work, inspect recovery history, refresh/check original request, link replacement, inspect evidence, accept one dependency, withdraw unconsumed evidence |
| PR run | Operator | Decision inbox row/filter and exact owner subject, Filtered run row, state/lease context, PR run page (actions, decisions, attempts) | Enroll PR, advance, pause, resume, cancel, attach PR, inspect decisions/attempts ; Review exact decision, filter pending work |
| Execution attempt | Operator | Summary row, request/reply timeline, retained evidence | Open history, inspect request/reply, follow provider/PR evidence |
| Run question | Operator | Decision inbox row/filter and exact owner subject, Pending question, answer editor, decision history | Ask, save answer, select answer for resume, dismiss, Check outcome, Retry same request ; Review exact decision, filter pending work |
| SDD unit | Operator | Decision inbox row/filter and exact owner subject, Branch document, proposal/readiness row and initial-stage/wait preview, milestone member/prerequisite row, waiting exact prerequisite and canonical lineage, effort selection | Browse, check readiness, select eligible subset, inspect suggested order, clear selection, start Planning, start Development, inspect execution lineage ; Review exact decision, filter pending work |
| SDD batch | Operator | Immutable selected order, state/revision/holds, phase preferences, admission claims and retained outcomes | Open execution selection, edit activity preferences, review selection, confirm create, load/open retained batch, pause/resume/stop future admission, refresh status, inspect native owner |
| Native SDD activity | Operator | Decision inbox row/filter and exact owner subject, Workflow stage/request panel, structured diagnostic/recovery guidance, evidence, exact retained outcome, approval/publication status, decision history | Answer request, approve integration, request revision, revoke approval, reject, Check outcome, Retry same request, Review publication reconciliation ; Review exact decision, filter pending work |
| Repository viewer | Operator | Branch selector, tree, file content, unit execution links, milestone selector and captured preview basis | Switch branch, browse file, refresh, preview milestone, open related run/PR |
| Webhook delivery | Operator | Event/outcome row, retained delivery identifiers | Filter noteworthy/status, page, refresh, inspect outcome |
| Notification channel | Operator | Destination card, credential/configuration form, delivery status, decision effective gates and destination context | Add, edit, enable/disable, send test, delete, open Decision notices, inspect Notice history |
| Operator notice | Operator | Exact observed subject link, immutable message membership, accepted/failed/unknown history | Inspect delivery, open exact review, review Send again, check outcome, retry same resend |
| Decision subscription | Operator | Project/kind selection, timing, revision and trust disclosure | Review/save, enable/disable, check save outcome, retry same save |
| System configuration | Operator | Read-only JSON record card | Refresh, inspect value |

Domain definitions and exclusions belong in [the glossary](glossary.md).
Element content, states and step-linked interactions belong in the
[UX documents](../ux/README.md). Product guarantees remain with their CAPs.
