---
title: Domain glossary
summary: "Read before naming product concepts or distinguishing scheduler, PR, SDD and SDK records; maps shared terminology to its owning contract and code."
---

# Domain glossary

| Term | Definition | Owner | Avoid | Code identifiers |
| --- | --- | --- | --- | --- |
| Project connection | One GitHub repository's saved connector, policy and verification configuration; excludes an individual execution. | `CAP-PROJ-project-connections` | repository task | `Project`, `projects` |
| PR run | Durable delivery of one enrolled PR through implementation, observation and merge/control outcomes. | `CAP-PR-pull-request-delivery` | job, SDK run | `PipelineRun` |
| Execution attempt | One implementation/fix request within a PR run, with immutable request and delivery correlation. | `CAP-PR-pull-request-delivery` | scheduler attempt | `ExecutionAttempt` |
| Run question | A request for operator input bound to a PR run and its attempt/head; a saved answer does not itself resume work. | `CAP-PR-operator-decisions` | approval, command | `RunQuestion`, `RunAnswer` |
| Work Plan | A batch of pre-PR requirements with Plan dependencies and admission controls. | `CAP-WORK-work-plan-execution` | SDD proposal | `WorkPlan` |
| Work Item | One requirement within a Work Plan, linked to its admitted PR run and retained result. | `CAP-WORK-work-plan-execution` | SDK task | `WorkItem` |
| Work Item replacement link | Retained relation between original and distinct replacement Work Items; excludes execution ownership. | `CAP-WORK-work-plan-execution` | successor substitution | `ReplacementLink` |
| Work Item dependency acceptance | Explicit confirmed replacement merge evidence for one existing local Item edge; excludes Item success and PR approval. | `CAP-WORK-work-plan-execution` | replacement approval | `ReplacementAcceptance` |
| AI catalog | Admission gateway for one provider account or plan, including quota and concurrency state. | `CAP-AGENT-catalog-admission` | connector, execution adapter | `AICatalog` |
| Connector | Saved provider credentials and provider identity; excludes the account's quota/admission policy. | `CAP-PROJ-project-connections` | AI catalog | `Connector` |
| Provider session | Tracked Jules work delivering a report or a PR; excludes the schedule invocation and the adopted PR run. | `CAP-AGENT-provider-sessions` | schedule job | `AICatalogSession` |
| Connection test | Isolated diagnostic work with its own execution, ownership and cleanup evidence. | `CAP-CONN-connection-verification` | development run | `ConnectionTest` |
| Schedule configuration | Trigger and payload of a registered scheduler task; excludes its individual execution history. | `CAP-EXEC-scheduling-maintenance` | Work Plan | `ScheduleConfig` |
| Schedule job | One recorded scheduler execution, including attempts, logs and retry outcome. | `CAP-EXEC-scheduling-maintenance` | PR run | `ScheduleJob` |
| System maintenance | Protected shared schedule for retained background work and cleanup. | `CAP-EXEC-scheduling-maintenance` | external tick | `system.maintain` |
| SDD unit | A connected repository's native proposal or change spec used by devkit workflow evaluation. | `CAP-SDD-native-delivery` | Work Item | `spec_dir`, `unit_kind` |
| SDD batch | Immutable selected sequential native-unit intent and retained admission/control evidence; excludes a Work Plan, a native activity and its PR run. | `CAP-SDD-native-delivery` | batch job, Work Plan | `SddBatch`, `SddBatchMember` |
| Native SDD activity | Hub admission and execution of repository-native Planning or Development work. | `CAP-SDD-native-delivery` | SDK flow | `activity_kind` |
| Repository viewer | Read-only access to a selected branch's documents and recorded execution lineage. | `CAP-DOC-repository-viewer` | execution coordinator | `RepositoryService` |
| SDK task/flow run | External manifest execution in the SDK host's durable ledger; excludes PR and scheduler runs. | `CAP-SDK-task-flow-execution` | PR run, schedule job | `RunView`, `sdk_flow_runs` |
| SDK release | Immutable manifest and executor-binding identity admitted by the task/flow host. | `CAP-SDK-task-flow-execution` | deployment image | `ReleaseSpec` |
| Existing-PR bridge | Evidence-checked, scoped resumption of a paused PR run by a native SDK execution target. | `CAP-SDK-existing-pr-bridge` | second PR executor | `autohub.sdd`, `autohub.pr_delivery` |
| Operator notice | A notification about execution state, delivered through configured outbound channels; excludes the saved destination. | `CAP-NOTIFY-operator-notifications` | execution approval, Notification channel | `format_notice`, `Delivery` |
| Decision subscription | Opt-in project/kind/delivery settings for one global Notification channel; excludes the owner decision and authenticated identity of chat participants. | `CAP-NOTIFY-operator-notifications` | decision approval, recipient account | `DecisionSubscription` |
| Notification channel | A saved outbound destination with its sealed bot credential, severity threshold and delivery status; excludes an individual Operator notice. | `CAP-NOTIFY-operator-notifications` | notice event | `NotificationChannel` |
| Account | A human identity with approval, activation and administrator status; excludes a Browser session or machine identity. | `CAP-ACCESS-authentication-authorization` | Machine, Browser session | `UserReadAdmin`, `auth_version` |
| Machine | A registered automation identity with scopes and activation state that owns Machine keys; excludes a provider Connector. | `CAP-ACCESS-authentication-authorization` | Account, Connector | `MachineRead`, `MachineCreate` |
| Task specification | The registered scheduler task name, description and payload schema; excludes a Schedule configuration or Schedule job. | `CAP-EXEC-scheduling-maintenance` | change spec, SDD unit | `TaskSpecResponse` |
| Webhook delivery | A recorded authenticated GitHub event and its routing/processing outcome; excludes a PR run or its Execution attempt. | `CAP-PR-webhook-advancement` | PR delivery | `GitHubWebhookDelivery` |
| System configuration | A named JSON configuration record shown by the settings interface; excludes a Project connection's automation policy. | `ARCH-05-2-components` | Project connection settings | `SystemConfig` |
| Browser session | A signed-in human account's access/refresh session. | `CAP-ACCESS-authentication-authorization` | machine credential | `autohub_refresh` |
| Machine key | A scoped credential for a registered machine; excludes human account approval. | `CAP-ACCESS-authentication-authorization` | browser token | `X-API-Key` |
| Work MCP endpoint | The fixed tool surface for ordinary work and its scoped mutations. | `CAP-MCP-tool-access` | operations endpoint | `/mcp/` |
| Operations MCP endpoint | The separate surface for project configuration and connection-test mutations. | `CAP-MCP-tool-access` | ordinary work endpoint | `/ops/mcp/` |

Approval belongs to the operation being authorized. PR ready status, an SDD
proposal decision, account approval and SDK approval do not authorize one another.
Use the owning contract when naming an approval subject; retain exact API field
names in code and payload examples.
