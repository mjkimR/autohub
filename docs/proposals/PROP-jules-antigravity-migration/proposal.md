---
id: PROP-jules-antigravity-migration
title: Migrate Jules integration to Antigravity Remote Agents
summary: "Retire Jules integration and assess a supported Antigravity Remote Agents execution path while preserving existing session and delivery history."
status: reviewing
created_at: 2026-11-06
target_area: capabilities/agents/
priority: low
size: L
planning_effort: high
dev_effort: high
boundaries:
  owns:
  - modules/hub/app/features/ai_catalogs/
  - modules/hub/app/features/project_management/agent_schedules/
  - modules/hub/app/features/execution/
  - modules/hub/app/features/configuration/connectors/
  - modules/hub/migrations/
  - modules/hub/tests/
  - modules/hub-ui/src/lib/
  - modules/hub-ui/src/routes/
  - docs/capabilities/agents/
  - docs/usecases/
  - docs/ux/
  - docs/operations/
  - docs/steering/
  excludes:
  - .github/
  - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-jules-antigravity-migration] Migrate Jules integration to Antigravity Remote Agents

## 1. Background & Hypothesis

The operator does not plan further Jules feature investment and wants the existing integration retired in favor of an Antigravity Remote Agents path. This is future migration work, not an instruction to disable currently configured sessions or delete their evidence now.

`CAP-AGENT-provider-sessions` owns scheduled Jules sessions, report collection and task PR adoption. `CAP-AGENT-catalog-admission` owns shared provider admission. A replacement should preserve those product boundaries where the target provider offers a supported automation interface, while leaving PR delivery with `CAP-PR-pull-request-delivery`.

The official [Antigravity Remote Agents documentation](https://antigravity.google/docs/remote-agents/) describes Google-managed remote execution and the `agy --remote-agent` CLI entry point. This establishes a candidate execution surface, not compatibility with Jules APIs or a proven unattended Hub integration. Authentication, supported automation, durable identity and outcome collection remain Planning questions. No Jules shutdown date or API removal schedule is asserted by this proposal.

Recommended scheduling: follow the queued MCP tools, decision notifications and Work Plan templates unless provider availability makes retirement urgent. The ordering is a product preference, not a dependency on `SPEC-mcp-delivery-tools`, `SPEC-decision-notifications` or `SPEC-work-plan-templates`.

## 2. Technical Spike Questions

- **Q1**: Does Antigravity provide a supported noninteractive API or CLI contract for creating, identifying, observing and resuming remote sessions, with credentials usable by Hub's execution environment?
- **Q2**: Which task/report, repository binding, PR result, human-input, quota and cancellation semantics can be mapped, and which existing Jules behaviors cannot be carried over?
- **Q3**: How can response-loss recovery distinguish an existing remote session from a never-created one without an unsupported retry or duplicate remote effect?
- **Q4**: What is the retirement path for existing Jules schedules, credentials, catalogs, pending sessions and retained reports/PR links? Which records remain readable after the provider implementation is removed?
- **Q5**: Can replacement and retirement form one bounded migration spec? If supported integration or cutover requires independently deliverable work, decompose the draft before direction acceptance.

## 3. Proposed Design & Impact

### Candidate scope

- Inventory Jules-specific session execution, collection, catalog settings, schedules, credentials, UI and operational guidance. Stop adding Jules-only capabilities.
- Compare supported Antigravity API/CLI integration options using official documentation. Record an explicit feasibility decision and unavailable capabilities; do not assume internal endpoints or automate the provider's UI as a service API.
- If feasible, introduce an Antigravity provider execution path through existing admission and provider-session owners. Keep GitHub PR enrollment, CI, recovery and merge authority with their existing owners.
- Give newly created remote work durable provider-specific identity and recovery evidence. Old Jules session identities are never replayed against the replacement provider.
- Define an explicitly reviewed cutover for schedules and catalogs. Credentials and prompts are not silently portable, and an existing schedule must not start remote work solely because its provider configuration was migrated.
- Remove obsolete Jules execution code and creation/configuration UI when the agreed cutover conditions hold. Preserve historical session/report/PR relationships and readable retirement diagnostics; settle or explicitly retain uncertain pending work before disabling its reconciliation path.
- If no supported unattended integration exists, return a concrete retirement-only or deferred-integration direction for review. Do not represent the migration as delivered or silently discard the Antigravity portion.

### Candidate acceptance examples

- **MIGRATE-01**: Given retained Jules sessions and reports, when Jules execution support is retired, then their history and PR ownership links remain inspectable and no new Jules work is admitted.
- **MIGRATE-02**: Given an explicitly configured supported Antigravity binding, when a task is started, then its remote identity and repository basis are retained without treating an old Jules receipt as its identity.
- **MIGRATE-03**: Given a lost creation response or an uncertain pending legacy session, when recovery runs, then known evidence is reconciled or an explicit hold is retained rather than creating replacement remote work blindly.
- **MIGRATE-04**: Given an existing Jules schedule, when cutover is reviewed, then unsupported settings and credentials are disclosed and migration does not implicitly authorize execution.
- **MIGRATE-05**: Given unavailable target automation capabilities, when Planning concludes, then the limitation and proposed retirement/defer disposition are explicit before implementation acceptance.

### Non-goals

- **Scope Excluded**: additional Jules capabilities, a promise of one-to-one provider feature parity, automatic migration of credentials or in-flight remote tasks, destructive history cleanup, unsupported/private API scraping and a second PR delivery controller.
- **Scope Excluded**: unrelated Codex behavior changes, SDK flow expansion, monitoring, CI trigger changes and a live production rollout campaign.

## 4. Lifecycle & Retirement Criteria

This is queued feature migration work with high Planning and Development effort. Draft size L is provisional until the supported target automation surface is established. Planning must settle feasibility, preserved behavior, legacy pending-work disposition and cutover authority; split independently deliverable removal and integration scopes if necessary. No provider replacement, service shutdown or credential removal is authorized by adding this draft. Normal direction acceptance and handoff precede implementation.
