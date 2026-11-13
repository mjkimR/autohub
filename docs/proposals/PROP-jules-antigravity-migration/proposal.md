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
  - modules/hub/app/features/project_management/connection_tests/
  - modules/hub/app/features/project_management/pipeline_runs/adapters/registry.py
  - modules/hub/app/features/project_management/projects/schemas.py
  - modules/hub/app/features/scheduling/schedule_configs/system.py
  - modules/hub/app/features/execution/
  - modules/hub/app/features/configuration/connectors/
  - modules/hub/migrations/
  - modules/hub/tests/
  - modules/hub-ui/src/lib/
  - modules/hub-ui/src/routes/
  - docs/capabilities/agents/
  - docs/capabilities/connections/
  - docs/capabilities/projects/
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

The official [Antigravity Remote Agents documentation](https://antigravity.google/docs/remote-agents/) describes Google-managed remote execution and the `agy --remote-agent` CLI entry point. This establishes a candidate execution surface, not compatibility with Jules APIs or a proven unattended Hub integration. The 2026-11-13 official-source spike found interactive start/resume support, but no published unattended Remote Agents create, observe, outcome or response-loss recovery contract. Remote sessions explicitly exclude `--print`. Authentication, durable identity and outcome collection therefore remain unestablished for a Hub integration. No Jules shutdown date or API removal schedule is asserted by this proposal.

Recommended scheduling: follow the queued MCP tools, decision notifications and Work Plan templates unless provider availability makes retirement urgent. The ordering is a product preference, not a dependency on `SPEC-mcp-delivery-tools`, `SPEC-decision-notifications` or `SPEC-work-plan-templates`.

## 2. Technical Spike Questions

The official-source evidence, implementation inventory and incoming-reference map are retained in
[Planning feasibility evidence](materials/feasibility.md). This is source/document inspection, not a live provider
verification. No replacement implementation is ready for acceptance.


- **Q1**: Does Antigravity provide a supported noninteractive API or CLI contract for creating, identifying, observing and resuming remote sessions, with credentials usable by Hub's execution environment?
- **Q2**: Which task/report, repository binding, PR result, human-input, quota and cancellation semantics can be mapped, and which existing Jules behaviors cannot be carried over?
- **Q3**: How can response-loss recovery distinguish an existing remote session from a never-created one without an unsupported retry or duplicate remote effect?
- **Q4**: What is the retirement path for existing Jules schedules, credentials, catalogs, pending sessions and retained reports/PR links? Which records remain readable after the provider implementation is removed?
- **Q5**: Can replacement and retirement form one bounded migration spec? If supported integration or cutover requires independently deliverable work, decompose the draft before direction acceptance.

## 3. Proposed Design & Impact

### Planning options

| Option | Supported basis | Consequence |
| --- | --- | --- |
| **A — Defer the migration until an official Remote Agents automation contract exists (recommended)** | Remote Agents document interactive App/web/CLI starts and resume by conversation ID; the required unattended protocol is not established. | Keep this proposal as the migration destination and preserve current Jules behavior. Restart when official authentication, create identity, observation/outcome and response-loss recovery contracts can be verified together. |
| **B — Retire new Jules admission first; defer Antigravity integration separately** | Hub owns admission, schedules and retained history independently of a replacement provider. | Return to Backlog for decomposition into a bounded retirement child and a deferred replacement child. Retirement disables new Jules session/test work and new-work creation/configuration entry points, while preserving legacy collection, adoption, test cleanup and history until their cutover conditions hold. Connector enablement, credential repair and catalog reassignment needed for legacy recovery remain available until draining is complete. The minimal recovery implementation remains while required. |
| **C — Use local/headless Antigravity CLI or SDK instead** | Official headless CLI/SDK documentation is separate from Remote Agents. | This changes the requested execution surface and needs a separate proposal covering workspace isolation, deployment and outcomes. It is not a supported substitute within this migration. |

Option A is recommended because no urgent Jules shutdown or retirement deadline is established, and the requested
replacement cannot yet satisfy the existing recovery guarantees. Option B is viable only if the operator chooses
retirement independently of replacement availability. Option C is compared as a scope alternative, not selected.

### Preservation and cutover constraints

1. Existing `jules` catalog kinds, connector identities and tracked session identities are never renamed to an
   Antigravity identity. Reports, PR URLs, `pipeline_run_id` and `pipeline_run_retired_at` remain readable under their
   original provider.
2. Disabling new Jules admission does not stop collection of known or uncertain sessions or pending task PR
   adoption. The retirement plan must inventory their disposition before removing the collector or usable
   credentials. Connector enablement, credential repair and catalog reassignment required to restore legacy recovery
   remain available until draining is complete. A held/unconfirmed remote result is not proof that remote work stopped.
3. Existing connection tests retain their captured catalog/connector evidence, provider output discovery, positive
   cleanup ownership and enrollment/merge exclusion. The Jules recipe/recovery implementation is retained while a
   legacy test still needs it. Removing the registry entry alone would strand `adapter_for` and manual cleanup
   resolution, conflicting with `CAP-CONN-connection-verification`.
4. New schedules never become Antigravity schedules through a data backfill or catalog kind rewrite. An eventual
   replacement binding and its execution authority are explicit. No credential or prompt portability is assumed.
5. Scope expansion candidates discovered by the inventory are named in `boundaries`: connection-test adapters,
   the pipeline adapter refusal registry, project catalog schema references, schedule-system metadata and their
   owning connection/project contracts. They support retirement preservation; no PR delivery redesign is proposed.
6. No database backfill, destructive cleanup, provider removal or service cutover runs during Planning. A retirement
   child must define persisted cutover diagnostics and demonstrate old-row readability, new-admission refusal,
   continued pending collection/adoption, and unresolved test cleanup/protection with PostgreSQL and SQLite tests.
   Acceptance also covers a disabled/expired connector repaired after new admission is refused: legacy recovery
   resumes without permitting another new Jules session or connection test.

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

### Open direction decision

Choose option A (defer the full migration) or option B (retirement first with decomposition). Option A leaves the
migration work queued with the restart conditions above. Option B returns this proposal to Backlog with
`needs_decompose: true`; the Host's decomposer and user decision determine the child drafts before implementation.
No PADR is authored until that direction is selected, because an unchosen retirement policy must not be promoted
as an accepted decision. No screen is drafted while the scope is undecided.

This is queued feature migration work with high Planning and Development effort. Draft size L is provisional until the supported target automation surface is established. Planning must settle feasibility, preserved behavior, legacy pending-work disposition and cutover authority; split independently deliverable removal and integration scopes if necessary. No provider replacement, service shutdown or credential removal is authorized by adding this draft. Normal direction acceptance and handoff precede implementation.
