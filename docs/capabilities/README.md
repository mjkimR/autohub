# Capability contracts

Each capability owns implemented guarantees, interfaces, code entrypoints and
enforcing checks for one bounded area. Full IDs resolve the contracts independently
of their location. Source/test inspection does not establish a fresh test run or
production rollout; see [delivery status](../operations/deployment-status.md).

| Area | Capability IDs |
| --- | --- |
| Project configuration and connectors | `CAP-PROJ-project-connections` |
| PR delivery and operator questions | `CAP-PR-pull-request-delivery`, `CAP-PR-operator-decisions` |
| Operator debt across object types | `CAP-PR-owed-items` |
| CI observation and provider dispatch | `CAP-PR-ci-observation`, `CAP-PR-agent-dispatch` |
| Signed events and recoverable wakeups | `CAP-PR-webhook-advancement` |
| Pre-PR plans and dependencies | `CAP-WORK-work-plan-execution` |
| Account admission and provider sessions | `CAP-AGENT-catalog-admission`, `CAP-AGENT-provider-sessions` |
| Isolated connection diagnostics | `CAP-CONN-connection-verification` |
| Native repository SDD | `CAP-SDD-native-delivery`, `CAP-SDD-runtime-isolation`, `CAP-SDD-workflow-control` |
| Read-only repository documents and roadmap | `CAP-DOC-repository-viewer` |
| External task/flow execution and existing-PR bridge | `CAP-SDK-task-flow-execution`, `CAP-SDK-existing-pr-bridge` |
| Scheduling, jobs and shared maintenance | `CAP-EXEC-scheduling-maintenance` |
| Operator notification channels | `CAP-NOTIFY-operator-notifications` |
| Human and machine access | `CAP-ACCESS-authentication-authorization` |
| Scoped MCP surfaces | `CAP-MCP-tool-access` |

[Use cases](../usecases/README.md) describe the actor goals these contracts serve.
[Operations guides](../operations/README.md) retain setup and client instructions;
they do not replace the owning capability.
