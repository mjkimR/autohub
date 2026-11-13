---
id: SPEC-schedule-config-ownership
title: Schedule configuration ownership and project filter
summary: "Derive verified schedule owners and mutation metadata in bounded reads, and filter schedules by project before pagination."
status: in-progress
created: 2026-11-13
related_capabilities: [CAP-EXEC-scheduling-maintenance, CAP-AGENT-provider-sessions, CAP-PROJ-project-connections]
related_usecases: []
workflow: sdd-spec-feature
---

# [SPEC-schedule-config-ownership] Schedule configuration ownership and project filter

## 1. Problem Statement & Motivation

The generic schedule list guesses ownership from task names and payloads, exposes protected actions and cannot resolve retained test/agent owners. Project Automation scans all projects and a bounded test history. `ADR-schedule-owner-projection` selects derived ownership without stored owner columns.

## 2. User Stories

- As an operator, inspect a verified schedule owner and use only permitted generic mutations.
- As an operator, filter schedules by project and inspect Automation without an all-project scan.

## 3. Non-Goals

1. **Scope Excluded**: changing mutation authority, execution, due-time logic, stored schema or historical rows.
2. **Scope Excluded**: exact agent/test row deep links, a new dashboard, provider migration or dependency changes.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Consistent owner reads
- **Given** every owner kind and unlinked provider tasks
- **When** list, detail or successful create/patch/put returns a configuration
- **Then** owner kind, verified nullable IDs and generic mutation permission follow the accepted precedence table.

### [AC-02] Project filter parity
- **Given** mixed owners across projects
- **When** project_id composes with search, task, enabled, ordering and pagination
- **Then** rows and count cover only resolved owners without duplicates; unknown project is empty and malformed query UUID returns 422.

### [AC-03] Unresolved references
- **Given** malformed, nonstring or dangling payload IDs
- **When** reads and project filtering run on SQLite or PostgreSQL
- **Then** reads succeed with unresolved nullable IDs and filtering excludes unresolved owners; reserved tasks stay protected.

### [AC-04] Owner-aware actions
- **Given** resolved, unresolved protected and editable rows
- **When** the generic screen renders
- **Then** verified owner links name the project and target Automation or Connections, only permitted generic actions appear, and crafted protected mutations still receive 409.

### [AC-05] Retained test ownership
- **Given** more than 30 retained connection tests and an older test schedule
- **When** project Automation loads schedules
- **Then** a paginated project-filtered read supplies dispatch/observation/test groups without a separate tests read or cross-project scan; agent schedules remain separate.

### [AC-06] Bounded reads
- **Given** pages of 1 and 50 mixed configurations on SQLite or PostgreSQL
- **When** a counted HTTP list read runs
- **Then** at most five SQL statements and one connection checkout occur, independently of page size; skip_count omits the count.

### [AC-07] Project selector recovery
- **Given** pagination and a selected Project filter
- **When** selection is changed/cleared or project options fail
- **Then** filter changes reset page one and compose project_id; options failure has Retry, preserves selection and leaves unfiltered reads usable.

AC-01 through AC-07 implement accepted OWNER-01 through OWNER-07 respectively.

## 5. Design Contracts and Screens

Resolution order is system.maintain; pipeline.dispatch_project; pipeline.connection_test; remaining agent-owned configuration; remaining pipeline.observe_project; operator. Reserved and agent-owned rows deny generic mutation; observation/operator rows allow it. Existing guard authority is preserved. IDs come only from retained owners/projects. Canonical and unhyphenated UUID strings are supported; malformed/nonstring values are unresolved.

`PROP-schedule-config-ownership-target` carries the accepted Screens and six-document ledger. Reuse that layout and verified project names with ID fallback; no new screen alternative is selected. Inspection of current source confirms the carried premises. Development runs at medium effort with independent code and reconciliation reviews. No live rollout is included.

## Implementation assumptions

Existing PATCH permits clearing both triggers. Read DTO validation preserves those manual-only persisted rows; mutation input validators are unchanged. Internal dispatcher DTO defaults preserve its construction without owner queries, while every public CRUD read explicitly projects owner metadata. The shared pagination dependency did not copy skip_count; the schedule-local dependency now applies the accepted option explicitly.
