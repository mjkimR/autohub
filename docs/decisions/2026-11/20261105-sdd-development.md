---
id: ADR-sdd-development
title: Use devkit SDD for Auto Hub development
summary: "For Auto Hub's cross-feature delivery contracts, we use devkit SDD with a small catalog selection to keep changes traceable, accepting workflow and toolchain maintenance."
status: accepted
created_at: 2026-11-05
---

# [ADR-sdd-development] Use devkit SDD for Auto Hub development

- **Status**: Accepted
- **Date**: 2026-11-05
- **Deciders**: Repository owner
- **Involved Components/Capabilities**: Repository contributor tooling, backend, UI and SDK development

## 1. Context & Problem Statement

Auto Hub coordinates PR delivery, native SDD activities and SDK flows with
different execution and approval contracts. Its capability, use-case and
architecture documents describe these boundaries. Contributor tooling needs to
keep future changes and their verification aligned with those documents.

The existing development environment supplies devkit's harness and app-common
guidance. Native SDD execution for connected repositories already has separate
runtime manifests; those runtimes do not configure Auto Hub's own development.

## 2. Decision Drivers

- Trace changes across the backend, UI, SDK and their current contracts.
- Reuse the reviewed devkit release and existing project verification commands.
- Keep optional agent assets limited to operations used in this repository.

## 3. Considered Options

- **Adaptive development with document checks**: keeps iteration lightweight,
  with less structured planning and delivery reconciliation.
- **SDD with document checks and selected catalog assets**: provides workflow
  routing and reconciliation for contract changes, with additional tooling and
  delivery records when the selected workflow requires them.

## 4. Decision Outcome

We chose SDD for traceable changes to the retained product contracts.

- The root development environment uses `devkit-spec` as its direct base package,
  bringing the harness and document system at the reviewed immutable revision.
- Shared development policy explicitly selects `sdd`; existing approval policies
  remain in effect. The selected workflow determines planning depth.
- The catalog selection consists of `command-design:core` for existing justfile,
  CLI and MCP entry points, and `maintenance:upkeep` for consistency and cleanup
  procedures. Other optional entries remain unselected until needed and approved.
- Contributor tooling remains separate from the connected-repository runtime
  manifests. The adoption adds no retrospective delivery or approval records.

## 5. Consequences

Contract changes receive the planning, review and reconciliation required by
their workflow. Session-level work can remain free of spec Unit records.
Contributors maintain the pinned packages, synchronized assets and installation
receipt alongside normal code and document changes.

Reconsider catalog selections when a concrete operation needs another entry.
Package updates still require review against the runtime pins and viewer receipt.

## 6. Confirmation

- `uv run devkit spec policy` reports shared `sdd` policy and the approval gates.
- `uv run devkit status` and `uv run devkit sync --check` verify deployed assets.
- `just check-devkit` checks package inventories and immutable source identity.
- `just docs-check` checks current document rules and hygiene.
- Review only: the `/spec` intake and reconciliation follow the installed
  guidance; passing document checks alone does not prove semantic agreement.
