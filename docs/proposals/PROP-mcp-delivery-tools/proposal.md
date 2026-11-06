---
id: PROP-mcp-delivery-tools
title: Expose delivery decisions and recovery through MCP
summary: "Expose decision discovery, request outcomes, SDD batch controls and Work Item recovery through scoped MCP tools that reuse their existing business owners."
status: draft
created_at: 2026-11-06
target_area: capabilities/mcp/
priority: high
size: L
planning_effort: high
dev_effort: high
boundaries:
  owns:
  - modules/hub/app/mcp/
  - modules/hub/tests/integration/mcp/
  - modules/hub/tests/unit/mcp/
  - docs/capabilities/mcp/
  - docs/usecases/mcp/
  excludes:
  - docs/operations/
  - .github/
  - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-mcp-delivery-tools] Expose delivery decisions and recovery through MCP

## 1. Background & Hypothesis

`CAP-MCP-tool-access` exposes existing run and Work Plan operations, but the completed decision inbox, exact outcome reads, SDD batch controls and Work Item recovery/replacement remain outside its registered tool surface. Operators using a conversational client must switch to the UI to use those capabilities.

Expose those existing business operations through the Work MCP endpoint. The hypothesis is that one conversational task can discover a pending decision, inspect its exact owner evidence and invoke an explicitly selected supported next operation without reconstructing identities from unrelated screens.

Recommended delivery order: first, before `PROP-decision-notifications` and `PROP-work-plan-templates`. This is a priority recommendation, not a dependency between those proposals.

## 2. Technical Spike Questions

- **Q1**: Which owner operations are compatible with machine identity, and which human-only decision mutations must remain unavailable to MCP callers?
- **Q2**: What bounded typed tool inputs and results preserve project visibility, exact subject selection, current revisions and immutable request identities?
- **Q3**: How should unknown outcomes, retired records and stale evidence be disclosed without issuing a replacement request or implying approval?

## 3. Proposed Design & Impact

### Candidate scope

- Add read tools for cross-project pending decisions, exact owner request outcomes, SDD batch/member status, Work Item recovery and replacement evidence.
- Add work mutations for existing batch pause/resume/stop, Work Item recovery and replacement link/accept/withdraw operations, subject to the existing owner's actor policy. Resolve unsupported machine actor cases during Planning rather than impersonating a person.
- Reuse existing UseCases, visibility checks, revision fences, request replay and scope enforcement. Extend `CAP-MCP-tool-access` and `UC-connect-hub-tools`; keep execution and evidence rules with their owning capabilities.
- Return bounded structured evidence, exact identities and actionable owner errors. Preserve the separation between reading an outcome, retrying the same request and issuing a fresh command.
- Retain Work versus Operations endpoint separation. Discovery does not authorize mutation, and a tool call does not grant native proposal/integration authority.

### Candidate acceptance examples

- **MCP-01**: Given an accessible pending decision, when queried through MCP, then its exact owner identity and observed basis can be inspected without exposing another project's evidence.
- **MCP-02**: Given a batch control or recovery request, when an identical request is replayed after a lost response, then the owner returns retained evidence without duplicate execution.
- **MCP-03**: Given missing write scope, stale revisions or unsupported actor authority, when a mutation is invoked, then it is refused without bypassing owner policy.
- **MCP-04**: Given a missing or ambiguous outcome, when read through MCP, then the tool reports uncertainty without creating a new request or claiming completion.

### Non-goals

- **Scope Excluded**: new delivery controllers, automatic approvals, natural-language execution planning, implicit retries, new OAuth provisioning, provider/Jules tools and SDK flow expansion.
- **Scope Excluded**: production rollout, live-provider verification, monitoring and CI changes.

## 4. Lifecycle & Retirement Criteria

This is queued feature work with high Planning and Development effort. Planning settles the machine actor boundary, exact tool inventory and schemas; no direction acceptance or implementation is recorded. Compare the adapters with `CAP-PR-operator-decisions`, `CAP-SDD-native-delivery`, `CAP-SDD-workflow-control` and `CAP-WORK-work-plan-execution`. Retire through the normal accepted proposal handoff after those choices are reviewed.
