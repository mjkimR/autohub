---
id: PROP-mcp-delivery-tools-target
title: Living Spec targets for MCP delivery tools
summary: "Map MCP delivery adapters to their transport capability and machine-client use case without changing owner execution semantics."
status: draft
---

# [PROP-mcp-delivery-tools-target] Living Spec targets for MCP delivery tools

## Capability ledger

| Target | Change |
| --- | --- |
| `CAP-MCP-tool-access` | Add the 12 tool names, typed input/output and bounded collection disclosures; distinguish persisted reads from write-scoped exact review; machine actor/replay and existing owner reuse remain explicit. |

## Use cases

| Target | Change |
| --- | --- |
| `UC-connect-hub-tools` | Extend step 5 examples for discovery/exact review/outcome lookup and machine-selected batch/recovery/replacement actions; add stale basis, unknown request and actor mismatch extensions. |

## Decisions

Promote `PADR-mcp-delivery-owner-adapters` and update its Confirmation with actual implementation/review evidence. Do not modify existing execution-owner ADR decisions.

## Screens

No product UI changes or screen drafts. The surface is the typed MCP tool registry; current decision and Work Plan screens retain their existing behavior.

## Before and after

Before: conversational clients lack these owner adapters. After: scoped machine tools expose allowlisted evidence and exact existing commands. The proposal inventory and MCP-01–MCP-08 provide the expected behavioral comparison; no timing claim or live deployment claim is made.
