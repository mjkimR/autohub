---
reconcile_id: REC-mcp-delivery-tools
status: pending
targets:
  - file: docs/capabilities/mcp/CAP-MCP-tool-access.md
    resolution: modified
  - file: docs/usecases/mcp/UC-connect-hub-tools.md
    resolution: modified
  - file: docs/decisions/2026-11/20261106-mcp-delivery-owner-adapters.md
    resolution: modified
---

# Reconciliation: `SPEC-mcp-delivery-tools`

The transport capability records all12tools, scopes, machine actors, exact owner
replay and bounded allowlisted evidence. The use case covers changed basis and
lost-response replay. The ADR Confirmation identifies implementation checks;
its accepted decision is unchanged. Existing owner capabilities need no changes
because their contracts are reused. No product screen or new domain concept is
introduced. No agreed work is deferred.

Inspection is distinct from executed evidence: MCP56, owner/auth104 and7PostgreSQL
transport tests passed; just lint/check passed. The same-head registry baseline
without the four added registration functions exposes31tools; enabling them
exposes43 with all31existing names retained. No timing or live-provider claim.
