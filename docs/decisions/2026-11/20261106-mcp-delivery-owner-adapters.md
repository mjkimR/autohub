---
id: ADR-mcp-delivery-owner-adapters
title: Keep MCP delivery adapters within owner authority
summary: For conversational delivery access, we use scoped machine adapters and allowlisted owner views, to preserve existing authority and replay semantics, accepting a deliberately limited tool surface.
proposal: SPEC-mcp-delivery-tools
status: accepted
created_at: 2026-11-06
---

# [ADR-mcp-delivery-owner-adapters] Keep MCP delivery adapters within owner authority

- **Status**: Accepted
- **Date**: 2026-11-06

---

## 1. Context & Problem Statement

Owner endpoints expose rich execution snapshots while MCP credentials represent machines. Proxying raw REST shapes would blur scope risk and disclose internal snapshot maps. Exact decision review persists inspection even though it does not submit a decision.

## 2. Decision Drivers

- Preserve owner actor-bound idempotency and native authority boundaries.
- Keep typed external schemas explicit and compatible with existing MCP tools.
- Expose bounded useful evidence without raw snapshots.

## 3. Considered Options

- UI-only: retains current boundaries but requires conversational context switching.
- Focused scoped adapters: reuses existing owners and explicitly projects safe evidence.
- Raw REST proxy: minimizes adaptation but conflates inspection risk and payload disclosure.

## 4. Decision Outcome

Choose focused scoped adapters because machine identity, side effects and output fields remain auditable.

- Machine actors derive only from the authenticated MCP subject; client-supplied human identity is refused. → `CAP-MCP-tool-access` delivery tool authority rules (MUST).
- Exact native inspection is a write-scoped tool, while persisted discovery/outcome reads use read scope. → `CAP-MCP-tool-access` delivery tool scope rules (MUST).
- New views project an explicit bounded field set and do not expose raw owner snapshots. → `CAP-MCP-tool-access` bounded disclosure rules (MUST).
- Owner eligibility, replay and original outcome rules remain authoritative; adapters create no second delivery controller. → `CAP-MCP-tool-access` business-rule reuse (MUST).

## 5. Consequences

Focused adapter/schema modules add mapping maintenance. The limited surface excludes batch creation and new native approval tools. No database or frontend change is required. If an owner shape changes, its MCP projection and schema regression tests need explicit review.

## 6. Confirmation

Planning review only. Development adds transport scope/identity tests, real owner replay/refusal tests and allowlist serialization tests under `modules/hub/tests/integration/mcp/`; existing MCP compatibility tests and architecture rules remain checks. Reconcile the outcome with `CAP-MCP-tool-access` and `UC-connect-hub-tools`. No product execution or deployment is established by this draft.
