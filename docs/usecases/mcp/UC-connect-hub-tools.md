---
id: UC-connect-hub-tools
title: Connect an agent to scoped Hub tools
summary: "An operator provisions a managed machine credential and connects an agent to Hub's work or operations MCP endpoint. The agent discovers tools and executes only operations allowed by its endpoint and scopes."
area: mcp
primary_actor: Operator
supporting_actors:
  - MCP client
status: active
capabilities:
  - CAP-ACCESS-authentication-authorization
  - CAP-MCP-tool-access
---

# [UC-connect-hub-tools] Connect an agent to scoped Hub tools

## 1. Goal

- **Goal**: give an agent access to the intended Hub tool surface with explicit
  machine authority.
- **Scope**: managed key administration and an MCP connection's first tool call.
- **Trigger**: the operator configures an agent's Hub connection.
- **Preconditions**: the Hub service and an MCP-capable client are available.

## 2. Main Success Scenario

1. The operator authenticates for machine-key administration
   (`CAP-ACCESS-authentication-authorization`).
2. The operator creates a machine with the intended scopes and issues its key
   (`CAP-ACCESS-authentication-authorization`).
3. The operator configures the MCP client for the intended endpoint and machine
   credential (`CAP-MCP-tool-access`).
4. The client initializes its authenticated connection and discovers that
   endpoint's tools (`CAP-MCP-tool-access`).
5. The client calls a discovered tool within its granted authority and receives
   the typed result (`CAP-MCP-tool-access`).

## 3. Extensions

- **1a.** No administration authority: Hub refuses credential administration;
  the use case ends without a new managed key.
- **4a.** Invalid or withdrawn key: Hub returns HTTP `401`; the operator replaces
  or repairs the credential and resumes at step 3.
- **4b.** Wrong endpoint scope: Hub returns HTTP `403`; the operator chooses a
  matching endpoint or scope and resumes at step 3.
- **4c.** Disallowed Origin: Hub returns HTTP `403`; the client must correct its
  origin/request configuration before resuming at step 3.
- **5a.** Tool authority missing: the call returns `MCP_FORBIDDEN`; the client may
  select a permitted operation and resume at step 5.
- **5b.** Invalid tool arguments: the call returns `MCP_INVALID_ARGUMENTS` with
  validation details; the client corrects its input and resumes at step 5.
- **5c.** Tool belongs to the other surface: the call is rejected even for a key
  holding all scopes; the operator configures the other endpoint and resumes at
  step 3.

## 4. Postconditions

- **Success guarantee**: the agent received a result from a tool registered on
  its endpoint and authorized by the machine's scopes.
- **Minimal guarantee**: refused transport or tool authority does not grant the
  requested operation; discovery does not authorize a mutation by itself.

## 5. Acceptance Criteria (Given / When / Then)

Rules exercised: administration authority from
`CAP-ACCESS-authentication-authorization`; authenticated transport, origin,
endpoint separation, tool scopes and typed arguments from `CAP-MCP-tool-access`.

### Scenario: Connect and read Hub work

- **Covers**: main success scenario.
- **Given**: an administrator-issued machine key with work-read scope.
- **When**: the client initializes, discovers and calls `projects_list` on the
  work endpoint.
- **Then**: discovery succeeds and the call returns a structured successful page.

### Scenario: Refuse unauthorized key administration

- **Covers**: 1a.
- **Given**: a caller without root or superadmin authority.
- **When**: they attempt machine-key administration.
- **Then**: Hub refuses the request without issuing a key.

### Scenario: Revalidate credentials on the next request

- **Covers**: 4a.
- **Given**: a previously working key is revoked, expired or its machine disabled.
- **When**: the client sends another discovery request.
- **Then**: Hub returns HTTP `401`.

### Scenario: Refuse an endpoint-scope mismatch

- **Covers**: 4b.
- **Given**: a work-only key.
- **When**: the client connects to the operations endpoint.
- **Then**: Hub returns HTTP `403` before a tool runs.

### Scenario: Refuse a foreign browser Origin

- **Covers**: 4c.
- **Given**: an otherwise valid machine credential.
- **When**: a request carries an Origin for another host.
- **Then**: Hub returns HTTP `403`.

### Scenario: Read-only discovery does not authorize a mutation

- **Covers**: 5a.
- **Given**: a work-read-only key that discovered `runs_cancel`.
- **When**: the client calls that mutation.
- **Then**: the call returns `MCP_FORBIDDEN` without canceling work.

### Scenario: Return actionable input validation

- **Covers**: 5b.
- **Given**: an authorized work connection.
- **When**: `projects_list` requests a page limit of 101.
- **Then**: the call returns `MCP_INVALID_ARGUMENTS` with the field's limit detail.

### Scenario: Keep tool registries disjoint

- **Covers**: 5c.
- **Given**: a machine key holding all MCP scopes.
- **When**: it calls an operations tool on the work endpoint.
- **Then**: the call is rejected because the tool is not registered there.

## 6. Evidence

Inspected checks: `modules/hub/tests/integration/auth/test_auth_api.py`,
`modules/hub/tests/integration/mcp/test_mcp.py`,
`modules/hub/tests/integration/mcp/test_work_decisions.py` and
`modules/hub/tests/unit/mcp/test_registration.py`. They use local application and
mocked provider boundaries. This document records inspected contracts, not a
new remote connection or a fresh execution of those suites.
