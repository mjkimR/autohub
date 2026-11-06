---
id: PLAN-mcp-delivery-tools
spec: SPEC-mcp-delivery-tools
---

# Technical plan: `SPEC-mcp-delivery-tools`

## 1. Architecture Overview & Impact

Explicit MCP adapters call existing UseCases using machine actor identity. No new owner transactions or persistence. `ADR-mcp-delivery-owner-adapters` supplies the decision; `PROP-mcp-delivery-tools-target` supplies contract targets.

## 2. Component Breakdown & Interface Contracts

Separate decision, batch, recovery and replacement adapters with typed allowlisted views. Registration uses existing scope/risk enforcement. Reuse strict command models. No raw owner maps cross the output boundary. Bounded nested results disclose counts and omissions.

## 3. Verification & Test Plan

Real handler MCP tests cover scopes, machine replay, exact lookup and owner refusals. Unit serialization probes inject private raw fields and oversized collections. Existing MCP/auth and owner regression suites, `just lint` and `just check` preserve compatibility. Baseline uses current head with the new registrations omitted; existing tool inventory remains unchanged.
