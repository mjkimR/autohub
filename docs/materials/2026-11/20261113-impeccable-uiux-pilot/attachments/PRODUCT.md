# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

A single operator: the owner of the connected repositories, working in focused desk
sessions to check runs and answer the decisions agents raise. Other accounts exist
only through administrator approval; no other audience is confirmed.

## Product Purpose

Autohub coordinates GitHub repositories and external coding agents so work reaches a
merged PR with as little operator involvement as possible. Success is unattended
throughput: agents deliver, and the operator steps in only on exceptions (pending
decisions, failures, holds, approvals). Product context: `docs/steering/product.md`.

## Positioning

Autohub owns execution coordination and its authorization evidence; GitHub owns
code, CI and the merge; external agents implement; devkit owns SDD workflow
definitions. Hub never marks a PR ready on the operator's behalf, so the exceptions
it surfaces are the operator's actual decision points.

## Operating Context

- Authenticated operator console (Operate register); no marketing or public surface.
- Entry paths: enrolled PRs, Work Plans, native SDD activities, SDK task/flow runs.
- Outbound operator notices link to exact review subjects; the decision inbox is the
  cross-project worklist of pending operator work.
- Deployed on Google Cloud Run; responsive SPA with a narrow-screen menu.

## Capabilities and Constraints

- Stack: SvelteKit 2 SPA, Svelte 5, Tailwind v4, shadcn-svelte (`modules/hub-ui`).
- Binding constraint: every documented use case in `docs/usecases/` must remain
  achievable. Beyond that, layout, navigation layers and screen structure may be
  rearranged or rebuilt entirely if the UX improves.
- Terminology follows `docs/steering/glossary.md`.

## Brand Commitments

- Canonical name: "Autohub". Repository docs currently say "Auto Hub"; this is a
  known discrepancy, not a second name.
- The "Scheduler Manager" subtitle is retired.
- Not binding: the current blue primary (shadcn default), the check-square favicon
  and the Server-icon mark.

## Evidence on Hand

Product contracts and UX inventories only (`docs/capabilities/`, `docs/usecases/`,
`docs/ux/`). No testimonials, customers, benchmarks or public claims exist; do not
fabricate them.

## Object model

Before structural UI work, read:

- `docs/steering/product.md`: product context
- `docs/steering/glossary.md`: object names
- `docs/steering/ux-objects.md`: representations and actions per role
- `docs/ux/`: UX documents for the affected screens
- `docs/usecases/`: use cases every redesign must keep achievable

## Product Principles

- Exceptions first: surface what needs the operator; keep healthy automation quiet.
- Decisions are the operator's: show the evidence needed to approve or act.
- Use-case coverage is the invariant; structure is negotiable.

## Accessibility & Inclusion

None established.
