# Extend provider support

Use this guide when implementing another quota policy, pipeline transport,
provider session type or isolated connection-test recipe. Current product behavior
belongs to `CAP-AGENT-catalog-admission`, `CAP-AGENT-provider-sessions`,
`CAP-CONN-connection-verification` and `CAP-PR-pull-request-delivery`.
`ARCH-05-2-components` owns the component map. Operator setup belongs in
[provider connections](../operations/provider-connections.md).

## Choose the extension boundary

Quota policies select by catalog `kind`; PR delivery adapters select by
`adapter`. A provider can support sessions or diagnostics without supporting
existing-PR delivery. Extend the boundary needed by the implementation rather
than adding an unsupported capability flag to make a control visible.

## Add a quota kind

1. Add the kind to `AICatalogKind` in
   `modules/hub/app/features/ai_catalogs/models.py`.
2. Implement `QuotaPolicy` from
   `modules/hub/app/features/ai_catalogs/policies/base.py`, including normalized
   config validation and the delivery/quota/hold hooks. Keep a typed policy model
   with `extra="forbid"`; inspect the existing Codex and daily-quota tests for
   boundary examples.
3. Register it in `ai_catalogs/policies/registry.py`. If the provider owns a
   credential-bearing catalog, add its connector kind in
   `configuration/connectors/schemas.py::ConnectorProvider` and map it in
   `ai_catalogs/services.py::CATALOG_CONNECTOR_PROVIDERS`.
4. Define the supported kind-to-adapter mapping in catalog creation. Add session
   work types only if a session implementation actually exists. Expose capabilities
   through the read model; project catalog controls consume `pipeline_delivery`,
   and session controls consume `session_work_types`/`connector_provider`.
5. If shared dispatch eligibility changes, update service admission and the SQL
   `AICatalogRepository.admits_dispatch` predicate together. Preserve the caller's
   transaction when a rejected admission records a policy transition. Use the
   existing ledger helper rather than a second accounting path.

## Add PR delivery

1. Implement `ExecutionAdapter` in
   `project_management/pipeline_runs/adapters/base.py`: `deliver`,
   `collect_replies`, and the silent/reply wait settings.
2. Register the implementation in `adapters/registry.py::_ADAPTERS`. An
   intentionally unsupported registered adapter belongs in `_NOT_IMPLEMENTED`
   until implemented; that boundary refuses it before quota reservation.
3. Follow `CodexGithubMentionAdapter` for durable delivery identity, reconciliation
   and the supplied authorization callback. Keep run transitions/persistence in
   the lifecycle; adapter work returns the protocol's receipt/reply objects.
4. Verify interruption, stale authorization and duplicate-delivery outcomes using
   existing pipeline integration fixtures before advertising pipeline capability.

## Add a connection recipe

1. Implement the `ConnectionTestAdapter` protocol in
   `project_management/connection_tests/adapters/base.py` with a serializable
   `ConnectionTestSpec`: prerequisites, phases, evidence links and creation/
   discovery/recovery capabilities.
2. Register its `(kind, adapter)` key in `adapters/registry.py::ADAPTERS`.
   Keep provider-specific behavior in the adapter. The shared engine and UI read
   recipe metadata instead of gaining provider conditionals.
3. Increment the recipe `version` when its verification contract changes.
   `connection_tests/configuration.py` includes recipe identity/version in the
   fingerprint; a changed contract must not appear to verify an older result.
4. Reuse the shared GitHub ownership/cleanup helpers where applicable. Add cases
   for lost creation responses, cancellation during I/O, late output, unrelated
   descendants, incomplete discovery and changed review heads.
5. Reuse `ai_catalogs/providers/jules.py` Source lookup and the production Codex
   usage-limit classifier when extending their existing recipes; avoid a separate
   diagnostic interpretation of provider identity or quota replies.

## Add session work

Use `execution/tasks/domains/jules/{task.py,service.py}` as the registered-task and
orchestration example. Add an async task with a typed payload, import its package
for discovery, and wire supported work types and project schedule derivation
through `agent_schedules/repos.py::SESSION_TASKS` and `session_payload`.
Keep a provider client under its owning feature, not in a duplicate diagnostic
client. Preserve separate tracked-session and scheduler-job lifetimes.

## Add UI controls

The existing registry is
`modules/hub-ui/src/lib/features/configuration/ai-catalogs/catalog-kinds.ts`.
Implement policy dialog props as `CatalogDialogProps` and register its label,
component and optional summary in `catalogKinds`. `AICatalogsView` uses capability
fields for connector/session controls; `ProjectSettingsForm` uses
`pipeline_delivery`. The connection panel consumes the options recipe contract.
After API schema changes, regenerate the typed client with `just gen-ui-api`.

## Instrument and verify

Use `app_layer_base.core.log.logger`, following the existing provider services.
Keep credentials and raw provider error bodies out of logs and stored diagnostics.
`pipeline_runs/transition_log.py` centrally logs ORM run-state changes; avoid
adding duplicate transition messages in each adapter. Operator-safe job errors
and request correlation follow `CAP-EXEC-scheduling-maintenance`.

| Change | Existing test navigation |
| --- | --- |
| Quota and shared admission | `modules/hub/tests/unit/features/ai_catalogs/policies/` |
| Catalog creation/control API | `modules/hub/tests/integration/features/ai_catalogs/test_create_catalog.py`, `test_ai_catalogs_api.py` |
| Provider API parsing/Source resolution | `modules/hub/tests/unit/features/ai_catalogs/providers/test_jules.py` |
| Session payload and orchestration | `modules/hub/tests/unit/features/execution/tasks/domains/jules/test_service.py`, `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py` |
| Project schedule ownership | `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py` |
| Diagnostic identity/cleanup/recovery | `modules/hub/tests/integration/features/project_management/connection_tests/` |
| Delivery, quota and restart fences | `modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py` |
| Shared collection | `modules/hub/tests/integration/features/execution/maintenance/test_maintenance.py` |
| Catalog controls and connection UI | `modules/hub-ui/src/lib/features/configuration/ai-catalogs/AICatalogsView.integration.test.ts`, `modules/hub-ui/src/lib/features/project-management/projects/ProjectDetailView.integration.test.ts`, `ConnectionTestRecovery.integration.test.ts` |

Run project verification from the repository root after initializing the backend:
`just lint`, `just check`, relevant `just test` paths and `just test-ui` for UI
changes. Check migrations against PostgreSQL with the established development
procedure; mocked provider responses establish local contracts, not live account
permissions or real quota behavior. See the
[development guide](README.md) for environment and test commands.
