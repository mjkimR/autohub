---
title: Product context
summary: "Read before choosing a feature boundary or describing Auto Hub; defines its operators, delivery paths and relationship to devkit."
---

# Product context

Auto Hub is a personal development automation service for operators coordinating
GitHub repositories and external coding agents. One project connection represents
one GitHub repository, independently of that repository's internal packages.

An operator can enroll an existing PR, register a Work Plan before PRs exist,
start a native devkit activity, or submit an SDK task/flow. These entry paths have
different execution records and approval subjects. Their common infrastructure
includes scheduling, provider admission, durable history and operator controls.

GitHub owns repository contents, PR revisions, CI results and the actual merge
outcome. External coding agents perform implementation. Auto Hub owns execution
coordination and its authorization evidence. Devkit owns repository-native SDD
workflow definitions and stage evaluation.

Auto Hub's support for SDD in connected repositories is separate from using
SDD to develop Auto Hub itself. Writing the product's capability and use-case
contracts does not activate a development lifecycle or establish a verified
production baseline.

Read `CAP-PR-pull-request-delivery` for PR delivery, `CAP-WORK-work-plan-execution`
for pre-PR batches, `CAP-SDD-native-delivery` for native SDD activities, and
`CAP-SDK-task-flow-execution` for external task/flow execution. The glossary
separates concepts that share names across these paths.
