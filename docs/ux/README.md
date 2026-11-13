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
| PR run | Execution attempts, Run questions, attached PR and, for SDD activities, descriptive intent and retained legacy evidence |
| AI catalog | Connector selection, admission/quota policies and collected Provider sessions |
| Provider session | Report or provider-session link and, when present, a PR or admitted PR run |
| SDD unit | Selected repository branch/document, descriptive activity intent and related Run/PR links |
| Schedule configuration | Registered Task specification, payload, due/activation state and Schedule jobs |
| Machine | Scope/activation state and its Machine keys; an issued key has a one-time presentation |
| Notification channel | Saved destination and delivery feedback for Operator notices |

These are interface relationships. Exact persistence, execution and authorization
contracts remain in the CAPs rather than being redefined here.

## Find an interface

Find screens, modals and panels through the document index:

```sh
uv run devkit docs list ux --limit 0
uv run devkit docs search "project settings" --kind ux
```

Each screen document identifies its route. `UX-app-shell` supplies navigation and
session controls around authenticated screens. `UX-sign-in` describes the
unauthenticated layout at the requested route, rather than a separate `/login`
route. Compare screen coverage with `modules/hub-ui/src/routes/`; component
filenames alone do not determine whether an element is a screen, modal or panel.

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
