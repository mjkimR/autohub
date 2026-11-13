---
id: PLAN-owed-counts-error-reason
spec: SPEC-owed-counts-error-reason
summary: "Retain shared counts failure metadata under the existing request and session fences, then reuse it in Projects."
---

# Counts failure reason implementation plan

## 1. Constitution & Invariant Review

No architecture or ADR change is required. The repair restores `UX-projects` while preserving `CAP-PR-owed-items` count semantics. Product code stays in feature-owned Svelte rune state and the existing component.

## 2. Architecture Overview & Impact

Add reactive `error` metadata beside the existing `OwedCountsStore.value`; do not change the count union. `refresh` uses the existing `apiErrorMessage` helper and applies counts and reason together under the captured session generation. Projects derives its tooltip reason from the shared store. Shell and Attention continue to consume only known counts.

## 4. Storage & State Management

The initial error is empty. API refusal takes precedence over accompanying data. Invalid totals and thrown requests yield `Needs-you counts are unavailable`. A valid response clears the reason; pending retries retain settled state. The in-flight and checked-at behavior is unchanged. No persistence or migration is involved.

## 5. Error Handling & Edge Cases

Reuse `apiErrorMessage` for nonempty API detail, with a fixed fallback. Invalid per-kind/project entries retain existing filtering. Obsolete success and failure responses cannot replace current counts or error metadata.

## 6. Verification & Test Plan

First add a real-store Projects regression and record Red before source edits. Extend store tests for initial state, failures, precedence, pending recovery and obsolete sessions. Reuse shell integration coverage for neutral unknown labels and request cadence. Run focused Vitest tests, full `just lint`, `just check`, document rules and a mandatory independent code review. Only `UX-projects` needs Living Spec reflection; no capability or use-case guarantee changes. Separate reconcile review is optional under the medium single-component exception only with explicit evidence.
