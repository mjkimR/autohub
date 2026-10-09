# Implementation plan

Feature: app/features/execution/flows, separate from PR PipelineRun. The backend
consumes the workspace SDK models, without adding backend imports to the SDK.
Router → UseCase → Service → Repository preserves transaction ownership.

SQL tables own provider/env CAS and machine ownership, immutable releases,
FlowRun, StepRun, Attempt and Command. Conditional SQL updates arbitrate revisions
and lease tokens on SQLite and PostgreSQL. Unique keys serialize request identities.

The worker first commits an intent, then calls native identity or an allowlisted
HTTP service via the shared client, then applies results under lease+revision
fencing. Existing intents are inspected; authoritative absence resubmits the same
ID. Cancel returns a tombstone/terminal result rather than assuming 404 proves
termination. Endpoints are resolved at registration and pinned with releases;
credential environment references remain separately rotatable.

System maintenance selects bounded ready runs, including expired approval waits.
Errors are isolated per run. Tests use isolated DBs/worker ports, file-backed
restart verification, PostgreSQL concurrency, real API auth, and migration roundtrip.


The backend image now builds the SDK runtime; copy its source and preserve the
SDK README in Docker context because Hatchling reads it for wheel metadata.
The existing observation-race test uses `isolated_sqlite_dispatch`, matching the
other observation tests: default SQLite StaticPool cannot isolate simultaneous
transactions on its single connection. PostgreSQL keeps concurrent dispatch.
