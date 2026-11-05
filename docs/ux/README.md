# UX and shared objects

Use this view to trace a domain object through its representations, available
actions and the element where an operator performs a task. The
[UX object register](../steering/ux-objects.md) lists shared representations and
calls to action; [the glossary](../steering/glossary.md) defines their boundaries.
Each UX document describes one implemented screen, modal or panel. Its content
tree names the displayed objects and facts; its states and interactions link the
surface to use-case steps and owning capabilities.

These documents describe inspected source. They do not assert browser execution,
visual review, accessibility certification or live-provider verification. Visual
tokens remain in `modules/hub-ui/src/routes/layout.css` and the UI components.

## Object relationships visible in the interface

| Starting object | Related representations and navigation |
| --- | --- |
| Project connection | Connector/catalog selections, connection-test results, project/agent schedules, Work Plans, repository documents and PR runs |
| Work Plan | Work Item requirements and dependencies, retained run/PR links, group, comments and activity |
| PR run | Execution attempts, Run questions, attached PR and, for native SDD, workflow requests/evidence and decision history |
| AI catalog | Connector selection, admission/quota policies and collected Provider sessions |
| Provider session | Report or provider-session link and, when present, a PR or admitted PR run |
| SDD unit | Selected repository branch/document, proposal readiness and related Native SDD activities/run links |
| Schedule configuration | Registered Task specification, payload, due/activation state and Schedule jobs |
| Machine | Scope/activation state and its Machine keys; an issued key has a one-time presentation |
| Notification channel | Saved destination and delivery feedback for Operator notices |

These are interface relationships. Exact persistence, execution and authorization
contracts remain in the CAPs rather than being redefined here.

## Screens and route coverage

| Route or entry condition | Element |
| --- | --- |
| Unauthenticated layout at the requested route | `UX-sign-in` |
| `/` | `UX-dashboard` |
| `/projects` | `UX-projects` |
| `/projects/[projectId]` | `UX-project-detail` |
| `/projects/runs` | `UX-pipeline-runs` |
| `/schedules/configs` | `UX-schedule-configs` |
| `/schedules/jobs` | `UX-schedule-jobs` |
| `/settings/connectors` | `UX-connectors` |
| `/settings/ai-catalogs` | `UX-ai-catalogs` |
| `/settings/notifications` | `UX-notifications` |
| `/settings/system` | `UX-system-settings` |
| `/operations/tasks` | `UX-task-specs` |
| `/operations/webhooks` | `UX-webhook-deliveries` |
| `/admin/users` | `UX-users` |
| `/admin/machines` | `UX-machines` |

`UX-app-shell` supplies navigation and session controls around authenticated
screens. Sign-in is a layout state, not a separate `/login` route. Route coverage
is checked against `modules/hub-ui/src/routes/`; component filenames alone do not
determine whether an element is a screen, modal or panel.

## Task surfaces within screens

| Area | Related elements |
| --- | --- |
| Project setup | `UX-project-create`, `UX-project-settings`, `UX-project-connections`, `UX-project-schedule`, `UX-agent-schedules` |
| Connection verification | `UX-connection-test-check`, `UX-connection-tests` |
| Work Plans | `UX-work-plans`, `UX-work-plan-editor` |
| PR delivery and operator input | `UX-enroll-pull-request`, `UX-attach-pull-request`, `UX-run-decisions`, `UX-attempt-history` |
| Native SDD | `UX-sdd-run`, `UX-sdd-workflow-request`, `UX-sdd-decision-history` |
| Repository inspection | `UX-repository`, `UX-sdd-proposals`, `UX-sdd-execution` |
| Catalog configuration | `UX-catalog-create`, `UX-catalog-connector`, `UX-catalog-concurrency`, `UX-catalog-availability`, `UX-catalog-daily-quota`, `UX-catalog-codex-refresh`, `UX-catalog-sessions` |
| Connector credentials | `UX-connector-create`, `UX-connector-edit` |
| Notification destinations | `UX-notification-editor` |
| Machine credentials | `UX-machine-keys`, `UX-issued-machine-key` |
| Schedule configuration | `UX-schedule-editor`, `UX-schedule-delete` |

## Task-flow boundaries

A UX document lists only use cases whose steps actually reach it. The use case
cites the element where an action happens or its result appears; background steps
with no visible outcome identify why they happen off screen. Global navigation,
filters and administrative controls without an existing actor-goal use case state
their purpose in the interaction table instead of inventing a task citation.

API/tool-only goals such as the ad-hoc CI observation query, MCP connection and
SDK task/flow execution have no dedicated browser screen in this inventory.
Their contracts and use cases remain authoritative. A browser's saved CI status
or PR run link does not turn those API goals into an implemented UI flow.
