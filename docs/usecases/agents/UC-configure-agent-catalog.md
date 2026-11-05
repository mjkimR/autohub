---
id: UC-configure-agent-catalog
title: Configure an Agent Catalog
summary: "An operator registers or updates an AI catalog with the provider, concurrency and quota controls needed for later work admission. Saving configuration does not verify provider credentials or dispatch work."
area: agents
primary_actor: Operator
supporting_actors: []
status: active
capabilities:
  - CAP-AGENT-catalog-admission
entrypoints:
  - modules/hub/app/features/ai_catalogs/api/v1.py
  - modules/hub/app/features/ai_catalogs/services.py
---

# [UC-configure-agent-catalog] Configure an Agent Catalog

## 1. Goal

- **Goal**: retain a catalog with the operator's intended provider and admission controls so later work uses explicit capacity and quota settings.
- **Scope**: Auto Hub AI catalog configuration.
- **Trigger**: the operator wants another catalog or needs to adjust an existing one.
- **Preconditions**: the operator has access to the running Hub's catalog management API.

## 2. Main Success Scenario

1. The operator inspects the available catalogs and their admission controls (`CAP-AGENT-catalog-admission`). Screen: `UX-ai-catalogs`.
2. The operator submits a new catalog's provider and desired configuration (`CAP-AGENT-catalog-admission`). Screen: `UX-ai-catalogs`, `UX-catalog-create`.
3. Hub validates the definition against the provider's connector and quota requirements (`CAP-AGENT-catalog-admission`). Screen: `UX-catalog-create`.
4. Hub stores the catalog with its provider adapter and normalized policy (`CAP-AGENT-catalog-admission`). Screen: `UX-catalog-create`, `UX-ai-catalogs`.
5. The operator reviews the saved catalog's availability, effective capacity and supported work types (`CAP-AGENT-catalog-admission`). Screen: `UX-ai-catalogs`.

## 3. Extensions

- **2a.** Existing catalog: the operator selects an existing catalog and submits supported control updates; Hub validates and saves those updates; resumes at step 5. Screen: `UX-ai-catalogs`, `UX-catalog-connector`, `UX-catalog-concurrency`, `UX-catalog-availability`, `UX-catalog-daily-quota`, `UX-catalog-codex-refresh`.
- **3a.** Duplicate creation key: Hub refuses with HTTP 409 `CONFLICT` without replacing the existing catalog; the use case ends. Screen: `UX-catalog-create`.
- **3b.** Invalid fields or quota configuration: Hub refuses with HTTP 422, using `INVALID_REQUEST` for domain-policy errors or schema-validation output for invalid request fields; the use case ends without saving the invalid mutation. Screen: `UX-catalog-create`, `UX-catalog-connector`, `UX-catalog-concurrency`, `UX-catalog-availability`, `UX-catalog-daily-quota`, `UX-catalog-codex-refresh`.
- **3c.** Invalid connector assignment: Hub refuses an unsupported or wrong-provider connector with HTTP 422 `INVALID_REQUEST`; the use case ends without saving the invalid assignment. Screen: `UX-catalog-create`, `UX-catalog-connector`.
- **3d.** Missing catalog on update: Hub refuses with HTTP 404 `NOT_FOUND`; the use case ends. Screen: `UX-catalog-connector`, `UX-catalog-concurrency`, `UX-catalog-availability`, `UX-catalog-daily-quota`, `UX-catalog-codex-refresh`.
- **4a.** Jules credentials not yet registered: Hub stores valid Jules policy settings with no connector; resumes at step 5 with credentials still unverified. Screen: `UX-catalog-create`, `UX-ai-catalogs`.
- **5a.** Intentionally disabled or held catalog: the operator retains the disabled state or future hold; the use case succeeds as configuration, with new dispatches still subject to the saved admission restriction. Screen: `UX-ai-catalogs`.

## 4. Postconditions

- **Success guarantee**: the catalog definition or accepted control update is persisted and visible with the effective capacity and availability derived from it; no provider task was dispatched by configuration alone.
- **Minimal guarantee**: an invalid creation creates no catalog, and a refused individual update preserves the prior value; earlier separately accepted updates are not rolled back as one batch.

## 5. Acceptance Criteria (Given / When / Then)

Rules used: `CAP-AGENT-catalog-admission` **Provider adapter**, **Unique key**,
**Atomic validation**, **Creation connector**, **Credential-independent registration**,
**Connector reassignment**, **Manual hold**, **Hold preservation**, **Concurrency control**.

### Scenario AGENT-01: Register a Codex catalog

- **Covers**: main success scenario.
- **Given**: a new catalog key and valid Codex settings.
- **When**: the operator creates the catalog and lists catalogs.
- **Then**: creation returns HTTP 201, the list contains its assigned `codex-github-mention` adapter and normalized Codex policy, and no provider work is started.

### Scenario AGENT-02: Update existing admission controls

- **Covers**: 2a.
- **Given**: an existing catalog.
- **When**: the operator saves valid concurrency and kind-specific policy updates.
- **Then**: each accepted mutation returns the saved catalog with an advanced revision; a Codex recovery probe still reports effective concurrency 1.

### Scenario AGENT-03: Refuse duplicate creation

- **Covers**: 3a.
- **Given**: an existing catalog key.
- **When**: the operator creates another catalog with that key.
- **Then**: HTTP 409 `CONFLICT` is returned and the original catalog remains unchanged.

### Scenario AGENT-04: Refuse invalid fields and policy boundaries

- **Covers**: 3b.
- **Given**: a new key or an existing catalog's saved controls.
- **When**: the operator supplies concurrency 0 or 1001, an invalid key, a policy field belonging to another kind, or a nonfuture hold time.
- **Then**: HTTP 422 is returned and the invalid individual mutation is not saved.

### Scenario AGENT-05: Refuse the wrong connector

- **Covers**: 3c.
- **Given**: a Codex catalog or a Jules catalog and a GitHub connector.
- **When**: the operator assigns a catalog connector to Codex or the GitHub connector to Jules.
- **Then**: HTTP 422 `INVALID_REQUEST` is returned and the assignment is not saved.

### Scenario AGENT-06: Refuse an update to an unknown catalog

- **Covers**: 3d.
- **Given**: no catalog with the requested key.
- **When**: the operator changes its concurrency.
- **Then**: HTTP 404 `NOT_FOUND` is returned and no catalog is created.

### Scenario AGENT-07: Register Jules before its credentials

- **Covers**: 4a.
- **Given**: a new key and a valid Jules daily task limit, with no connector.
- **When**: the operator creates the catalog.
- **Then**: HTTP 201 returns `jules-api` with `connector_id=null`; this does not establish a working provider connection.

### Scenario AGENT-08: Preserve intentional restrictions

- **Covers**: 5a.
- **Given**: an existing catalog with a future hold.
- **When**: the operator disables it and enables it again.
- **Then**: its refresh time remains recorded and new work stays subject to the retained hold.

The API and policy tests named in `CAP-AGENT-catalog-admission` provide automated
coverage for these contracts. This use case records source/test inspection; it
asserts neither a new test execution nor live provider readiness.
