---
id: OPS-mcp-client-connection-refusals
title: "MCP client connection and tool-call refusal routing"
status: active
summary: "Routes an MCP client that cannot connect to, discover or call Hub work or operations tools to the credential, endpoint-scope or tool-contract owner by HTTP status, MCP error code, endpoint and key; client UI and secret storage stay outside Hub evidence."
related_capabilities:
  - CAP-MCP-tool-access
  - CAP-ACCESS-authentication-authorization
related_usecases:
  - UC-connect-hub-tools
---

# [OPS-mcp-client-connection-refusals] MCP client connection and tool-call refusal routing

An MCP client reports that Hub tools are missing, the connection fails, or a call is refused. Hub checks a request in
layers: the Origin header, the bearer credential, the endpoint's admission scopes, the endpoint's tool registry and
then the tool's own scope and input schema. Clients often collapse these into one generic "connection failed" or
"tool unavailable" message, so the HTTP status or MCP error `code`, together with the endpoint path and the machine the
key belongs to, decides the owner.

## Routing

Transport refusals happen before MCP processing and return an HTTP status with a JSON `detail`. Tool refusals return
MCP results with `isError` set and structured `{ok, result, error}` content whose `error.code` names the refusal.

| Symptom or state | Discriminating evidence | Next useful owner |
| --- | --- | --- |
| Connection fails with authentication required | HTTP `401` with `WWW-Authenticate: Bearer realm="autohub-mcp"` and `detail` "A valid MCP machine key is required"; the key is absent, mistyped, carries a doubled `Bearer ` prefix, or is the root administration key or a human login token | [Client setup](../runbooks/access.md#client-setup) for the header and environment-variable shape; `CAP-MCP-tool-access` §3 rule 1 and §4 for which credentials are MCP credentials |
| A previously working connection starts failing with `401` | Same `401`; the key was revoked or expired, or its machine was disabled, as shown on **Machine keys** (`/admin/machines`) | [Rotation and connection recovery](../runbooks/access.md#rotation-and-connection-recovery); `CAP-MCP-tool-access` §3 rule 3 |
| Connection fails with forbidden on one endpoint | HTTP `403` with `detail` "An MCP scope for this endpoint is required"; the machine holds only work scopes at `/ops/mcp/`, only `autohub:mcp:ops` at `/mcp/`, or only `autohub:dispatch` | [MCP connections](../runbooks/access.md#mcp-connections) connection table; `CAP-MCP-tool-access` §3 rule 2 and §4 admission scopes |
| Connection fails with forbidden despite a correct key | HTTP `403` with `detail` "Origin is not allowed"; the request carries an `Origin` whose host differs from the request host | The MCP client's request configuration; `CAP-MCP-tool-access` §3 rule 4 |
| An expected tool is not listed, or calling it returns an error result | Discovery succeeds without that tool, because the tool belongs to the other endpoint's registry: `projects_create`, `projects_update`, `connection_tests_start` and `connection_tests_cancel` are only at `/ops/mcp/`, every other tool only at `/mcp/`; a key holding every scope does not change this | [MCP connections](../runbooks/access.md#mcp-connections) step 4; `CAP-MCP-tool-access` §3 rule 5 |
| A discovered tool refuses to run | `error.code` `MCP_FORBIDDEN`; the machine lacks that tool's scope, typically a work mutation called with only `autohub:mcp:read` | Machine scope administration in [MCP connections](../runbooks/access.md#mcp-connections) step 1; `CAP-MCP-tool-access` §3 rule 6 |
| A call is refused before it reaches Hub business logic | `error.code` `MCP_INVALID_ARGUMENTS` with `error.advisory.details` naming each field, for example `limit: Input should be less than or equal to 100` | The tool's typed input in discovery and `CAP-MCP-tool-access` §3 rule 7 and §4 |
| A call reaches Hub business logic and is refused | `error.code` is an application code such as `NOT_FOUND`, `CONFLICT` or `INVALID_REQUEST` | The domain capability that `CAP-MCP-tool-access` §4 names for that tool; for uncertain mutations, its recovery paragraph and [Rotation and connection recovery](../runbooks/access.md#rotation-and-connection-recovery) |
| Automation with an MCP key is refused on a Hub REST route | The same key works at `/mcp/` but a protected `/api/v1/` route refuses it as a bearer or `X-API-Key` credential | `CAP-MCP-tool-access` §3 rule 11; `CAP-ACCESS-authentication-authorization` §3 rule 2 for the credential that route accepts |

A slashless endpoint path answers HTTP `307` to the slashed path; a client that does not follow the redirect fails
before any row applies, so configure the trailing slash shown in [Client setup](../runbooks/access.md#client-setup).
For evidence that matches no row, take the exact HTTP status or `error.code` to `CAP-MCP-tool-access` §3 and §4.

## Normal-state observation

After the owner's action, the client's refreshed discovery at the configured endpoint returns that endpoint's fixed
registry, and `projects_list` on `/mcp/` returns a structured page with `ok` true. An operations connection is
confirmed by a successful `/ops/mcp/` discovery listing exactly the four operations tools. `CAP-MCP-tool-access` owns
these facts, and `UC-connect-hub-tools` owns the success contract.

## Authority boundary

The MCP client owns its connection UI, secret storage, restart behavior and how it surfaces a refusal. A successful
discovery or read does not prove that the machine may run a mutation, that a project's provider connection works, or
that provider work stopped after a client disconnect.

## Update triggers

- `CAP-MCP-tool-access` §3 rules 1–7 or 11, or the §4 endpoint, scope or tool tables change.
- The transport `detail` texts, status codes or check order in
  [auth.py](../../modules/hub/app/mcp/auth.py) change.
- Machine scopes in [auth.py](../../modules/hub/app/auth.py) gain or lose an MCP scope.
