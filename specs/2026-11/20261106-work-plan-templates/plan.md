---
id: PLAN-work-plan-templates
spec: SPEC-work-plan-templates
---

# Technical Plan: `SPEC-work-plan-templates`

## 1. Architecture

Router → TemplateUseCase → TemplateService/WorkPlanService → TemplateRepository. UseCase owns AsyncTransaction; Project then template/Plan locks serialize all writes. Add templates and actor-bound operation receipts without foreign keys to mutable historical Plan identities. Registration receipt and existing owner Plan creation commit atomically; only active registration invokes the ordinary post-commit kick.

## 2. Components

Strict definition/command DTOs; project-scoped soft-delete CRUD, exact outcome queries and template registration. Add one migration after a471ce28d100 and update older metadata roundtrip dependencies. Separate Templates management and provenance review from ordinary editor; persistent account/project session intent coordinates all template writes, exact read recovery and explicit retries. Session logout clears only its namespace. Use existing WorkPlanForm as editable payload editor with a typed seeded submit callback; do not duplicate owner execution logic.

## 3. Verification

Source-mirrored API tests for allowlist, replay/actor/route conflicts, atomicity, stale revision/binding, lifecycle and ordinary owner compatibility; PostgreSQL barriers for edit/delete versus registration and migration roundtrips. UI tests cover definition lifecycle, draft default, changed review, unknown responses/remount/reload, current versus original receipts and logout cleanup. Regenerate typed API, run just lint/check and scoped suites. Baseline: ordinary registration unchanged with templates unused; no performance claim.
