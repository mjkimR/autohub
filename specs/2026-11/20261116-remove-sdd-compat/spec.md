---
id: SPEC-remove-sdd-compat
title: Remove unused native SDD compatibility
summary: Remove native SDD history, retirement APIs and compatibility guards while preserving repository-owned activity publication and recovery.
status: completed
created: 2026-11-16
related_capabilities: [CAP-SDD-native-delivery, CAP-SDK-task-flow-execution]
related_usecases: [UC-start-sdd-activity, UC-complete-sdd-workflow]
workflow: sdd-spec-feature
---

# [SPEC-remove-sdd-compat] Remove unused native SDD compatibility

## 1. Problem Statement & Motivation

No legacy native SDD work exists to preserve. Retirement routes, historical batch surfaces,
version fences and built-in bridge recovery add unused behavior and misleading messages.
The operator requests complete removal of compatibility for that execution model.
Base: main at 71fa79386efdf617396c5a85ea746a3bdde601d5. No prerequisite work is required.

## 2. User Stories

- **US-1**: As an operator, I want only supported repository-owned SDD actions and ordinary PR controls.
- **US-2**: As a maintainer, I want unused native history and bridge compatibility removed from serving code and schemas.

## 3. Non-Goals

- **Scope Excluded**: unrelated compatibility in project connection payloads, schedule imports or Work Plan replacements.
- **Scope Excluded**: changing repository-owned activity publication, uncertain-publication recovery, PR ownership, generic SDK execution or deployment.
- **Scope Excluded**: rewriting completed specs or historical migration revision identifiers.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Remove native history and retirement surfaces
- **Given** the supported HTTP, MCP and UI surfaces.
- **When** their routes, tools and controls are inspected.
- **Then** no native batch history/control, native SDD decision, evaluator tombstone or retired-Run reconciliation surface remains.

### [AC-02] Preserve current activity safety
- **Given** Planning or Development publication, including a lost response or uncertain external effect.
- **When** the original request is retried or its uncertain no-Run claim is reconciled.
- **Then** existing request identity, project scoping, leases, exact artifact binding and duplicate-owner protection remain enforced without legacy version discriminators.

### [AC-03] Remove bridge compatibility
- **Given** generic SDK task/flow execution.
- **When** bindings are validated or workers advance.
- **Then** identity and configured HTTP execution remain supported, unknown native targets use ordinary binding validation, and no built-in SDD/PR bridge recovery or PR link model remains.

### [AC-04] Align storage and contracts
- **Given** a database upgraded through the revision chain and the current Living Spec.
- **When** schema and documentation checks run.
- **Then** unused native batch and bridge storage is removed by a forward migration, current activity claims remain available, and current contracts describe only supported execution.

## 5. Assumptions & Invariants

The operator confirms no legacy native execution needs preservation. Existing retirement/history
MUST clauses are replaced through ADR-remove-native-sdd-compatibility before implementation.
Development effort is medium because the change crosses backend, frontend and flow contracts.
