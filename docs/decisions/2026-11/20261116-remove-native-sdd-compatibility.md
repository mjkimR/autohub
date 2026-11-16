---
id: ADR-remove-native-sdd-compatibility
title: Remove unused native SDD compatibility
summary: "For a system with no legacy native work, we remove native history and retirement compatibility, to reduce unused product and execution paths, accepting no support for legacy records."
supersedes: [ADR-repository-owned-sdd-execution]
status: accepted
created_at: 2026-11-16
---

# [ADR-remove-native-sdd-compatibility] Remove unused native SDD compatibility

## 1. Context & Problem Statement

The operator confirms that no legacy native SDD execution exists to preserve.
Retirement endpoints, version fences, historical batch views and built-in SDK
bridge observation therefore serve no retained owner. Current repository-owned
activities still require durable publication claims and uncertain-effect recovery.

## 2. Decision Drivers

- Remove unused HTTP, MCP, UI and storage paths.
- Preserve current publication and ordinary PR ownership safety.
- Keep generic SDK task/flow execution independent of PR delivery.

## 3. Considered Options

1. Keep retirement/history compatibility: maintains unsupported product surfaces without legacy consumers.
2. Remove compatibility and its storage: reduces execution paths and requires no legacy-record support. Selected.

## 4. Decision Outcome

We remove native compatibility because no retained execution depends on it.

- Supported SDD surfaces expose repository-owned activities and current claim recovery. → `CAP-SDD-native-delivery` Supported interfaces (MUST).
- PR progression uses descriptive activity context without native version or retirement fences. → `ARCH-06-execution` SDD activity execution (MUST).
- SDK workers support configured generic targets without a built-in PR bridge or historical bridge observer. → `CAP-SDK-task-flow-execution` Worker bindings (MUST).
- A forward migration removes unused batch and SDK bridge link storage; migration revision identifiers remain valid.

Supersedes in part `ADR-repository-owned-sdd-execution`: the clauses requiring historical native evidence reads, old execution authority fences and retained SDK bridge records.

## 5. Consequences

Legacy native records and callers receive no compatibility support. Current uncertain
activity publication retains exact checkpoint inspection and explicit acknowledgment.
Generic PR controls, ordinary questions and generic SDK execution retain their owners.

## 6. Confirmation

`SPEC-remove-sdd-compat` AC-01 through AC-04 define surface, recovery, binding and
migration checks. Current source, focused integration tests, generated OpenAPI
and Living Spec review verify the absence of compatibility paths.
