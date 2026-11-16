---
id: SPEC-tick-continuation
title: Continue ready work without idle scheduler ticks
summary: "Bound immediate SDK flow transitions and SDD start/resume advancement while retaining admission limits and stable system schedule cadence."
status: completed
created: 2026-11-16
related_capabilities: [CAP-SDK-task-flow-execution, CAP-SDD-native-delivery, CAP-PR-pull-request-delivery, CAP-EXEC-scheduling-maintenance]
related_usecases: [UC-execute-task-flow, UC-start-sdd-activity, UC-complete-sdd-workflow, UC-run-due-work]
workflow: sdd-spec-feature
---

# [SPEC-tick-continuation] Continue ready work without idle scheduler ticks

## 1. Problem Statement & Motivation

Ready SDK steps, including final result validation, wait for another maintenance tick.
SDD activity registration and explicit PR resume commit ready work without trying to advance it.
System-owned interval schedules derive the next due time from arrival time and can skip an early subsequent tick.
The base is main at c13b87999496c352c96fe98b68efee12e8af80a7. This unit has no prerequisites.

## 2. User Stories

- **US-1**: As an operator, I want ready work to continue within a bounded invocation while real waits retain their due times and authority.

## 3. Non-Goals

1. **Scope Excluded**: resident timers, new queues, SDD workflow interpretation, implicit approval, pipeline batch reordering and changes to operator-owned interval semantics.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Continue ready SDK transitions
- **Given** synchronous completed worker results or authoritative absence for an existing attempt.
- **When** maintenance advances a flow.
- **Then** it continues ready transitions, reuses the absent attempt ID and validates the final result in the same invocation, within 32 advances and 20 seconds.

### [AC-02] Stop SDK continuation at real waits
- **Given** approval, pending external work, failure, changed ownership or an exhausted continuation budget.
- **When** a flow advances.
- **Then** it stops, preserves durable identity and fencing, and leaves due continuation for maintenance without polling before its due time.

### [AC-03] Advance committed activity and resume promptly
- **Given** successful SDD registration or explicit PR resume.
- **When** its durable transaction has committed.
- **Then** Hub attempts ordinary progression for at most 10 seconds; failure or timeout leaves registration/resume successful and work recoverable by ticks, without weakening project or catalog capacity, due time or lease checks.

### [AC-04] Preserve owned interval cadence
- **Given** a due system maintenance or project dispatch interval with a retained due instant.
- **When** a delayed tick claims it.
- **Then** the next due instant is the first interval boundary after now derived from that retained due instant, without replaying missed intervals; operator intervals and cron schedules retain their existing calculation.
