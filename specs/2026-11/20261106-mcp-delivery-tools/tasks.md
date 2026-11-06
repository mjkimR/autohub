---
id: TASKS-mcp-delivery-tools
spec: SPEC-mcp-delivery-tools
plan: PLAN-mcp-delivery-tools
---

# Tasks: `SPEC-mcp-delivery-tools`

- [x] **Task 1**: Implement twelve scoped owner adapters and safe bounded projections.
  - **_Boundary**: modules/hub/app/mcp/, modules/hub/tests/integration/mcp/, modules/hub/tests/unit/mcp/
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08_
  - **Verification**: new transport/projection and existing MCP/auth owner regressions; lint/types.
- [x] **Task 2**: Reconcile the retained public contracts and decision confirmation.
  - **_Boundary**: docs/capabilities/mcp/CAP-MCP-tool-access.md, docs/usecases/mcp/UC-connect-hub-tools.md, docs/decisions/2026-11/20261106-mcp-delivery-owner-adapters.md
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08_
  - **Verification**: independent code and reconciliation reviews; document rules.
