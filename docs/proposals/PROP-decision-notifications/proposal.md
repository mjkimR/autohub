---
id: PROP-decision-notifications
title: Notify operators about actionable delivery decisions
summary: "Deliver decision-focused notices with exact owner links, project and kind subscriptions, and bounded digests while preserving current decision authority."
status: draft
created_at: 2026-11-06
target_area: capabilities/notifications/
priority: medium
size: L
planning_effort: high
dev_effort: high
boundaries:
  owns:
  - modules/hub/app/features/notifications/
  - modules/hub/app/features/project_management/pipeline_runs/
  - modules/hub/app/features/project_management/sdd/
  - modules/hub/app/features/execution/
  - modules/hub/migrations/
  - modules/hub/tests/integration/
  - modules/hub-ui/src/lib/
  - modules/hub-ui/src/routes/
  - docs/capabilities/notifications/
  - docs/usecases/
  - docs/ux/
  - docs/steering/
  excludes:
  - docs/operations/
  - .github/
  - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-decision-notifications] Notify operators about actionable delivery decisions

## 1. Background & Hypothesis

`CAP-NOTIFY-operator-notifications` sends run stop/wait notices through configured Telegram channels. `CAP-PR-operator-decisions` supplies a cross-project decision inbox and exact owner review. Decision-focused delivery can connect those existing capabilities so the operator receives a relevant notice and opens the precise review subject.

The hypothesis is that project/kind subscriptions and bounded digests reduce repeated inbox polling while keeping decisions explicit in their owning UI.

Recommended delivery order: second, after `PROP-mcp-delivery-tools` and before `PROP-work-plan-templates`. The feature reuses existing decision and notification owners; it does not require the MCP proposal to be implemented.

## 2. Technical Spike Questions

- **Q1**: Which retained decision identity and generation distinguish a newly actionable decision, a still-pending one and a resolved/replaced subject for deduplication?
- **Q2**: Where should project and decision-kind subscriptions live, how do they intersect with channel severity settings, and how is recipient visibility enforced?
- **Q3**: How should immediate versus digest delivery, bounded accumulation and uncertain transport outcomes preserve useful notices without asserting exactly-once delivery?
- **Q4**: How can an authenticated deep link select the exact owner subject and safely explain changed, resolved or inaccessible evidence?

## 3. Proposed Design & Impact

### Candidate scope

- Add decision-focused notices for ordinary questions and supported native proposal, worker/workflow and integration decisions. Identify decision kind, project/run, waiting-age basis and a direct authenticated owner-review link.
- Add explicit project/kind subscriptions and an immediate or bounded digest preference using existing notification channels. Planning chooses defaults and limits; do not invent channel recipients from repository access.
- Reuse persisted decision evidence instead of evaluating repositories or contacting providers during notice formatting. Bound each maintenance pass and distinguish observation time from current live truth.
- Deduplicate by owner subject/generation and retained delivery evidence. Suppress resolved or inaccessible subjects where current owner evidence establishes that state; transport uncertainty must not become proof of delivery or decision completion.
- Reuse owner inspection on navigation. A stale link can explain replacement/resolution and offer fresh review, but cannot silently select or authorize another decision.
- Extend `CAP-NOTIFY-operator-notifications`, its owning use case and affected notification/inbox UI contracts during Development.

### Candidate acceptance examples

- **NOTICE-01**: Given a matching project/kind subscription and an actionable observed decision, when a notice is delivered, then its link opens that exact subject after authentication and fresh owner inspection.
- **NOTICE-02**: Given the same pending generation across maintenance ticks, when reconsidered, then retained delivery state prevents an ordinary duplicate notice; ambiguous transport remains explicitly uncertain.
- **NOTICE-03**: Given a digest window with multiple decisions, when delivered, then bounded content respects subscriptions and exposes exact review links without mutating decisions.
- **NOTICE-04**: Given a resolved, replaced or inaccessible subject, when its old link opens, then the UI explains its state and grants no authority over a replacement subject.

### Non-goals

- **Scope Excluded**: approval/reply commands in Telegram, bulk authorization, automatic resume, new transport providers, Jules questions and SDK machine approvals.
- **Scope Excluded**: health dashboards, monitoring, incident detection, production verification and CI changes.

## 4. Lifecycle & Retirement Criteria

This is queued feature work with high Planning and Development effort. Planning settles subscription ownership, bounded digest semantics, privacy and exact-link behavior. No new authority ledger or business approval is introduced. Acceptance and implementation follow the ordinary proposal lifecycle; deployment and real usage feedback are separate from the feature scope.
