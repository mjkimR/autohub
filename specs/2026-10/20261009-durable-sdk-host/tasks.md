# Tasks

- [x] SDK host models, repositories, catalog/run service and scoped auth APIs.
  Boundary: modules/hub/app/features/execution/flows/, modules/hub/app/auth.py,
  modules/hub/app/router.py, modules/hub/app/main.py, modules/hub/pyproject.toml,
  uv.lock, docker/hub.Dockerfile, .dockerignore. Requirements: AC-01, AC-02, AC-03, AC-04.
- [x] Durable worker, native/HTTP adapters, maintenance integration and recovery tests.
  Boundary: modules/hub/app/features/execution/flows/,
  modules/hub/app/features/execution/tasks/domains/maintenance/task.py,
  modules/hub/tests/integration/features/execution/flows/. Requirements: AC-03..07.
- [x] Migration, schema generation and full verification.
  Boundary: modules/hub/migrations/versions/, modules/hub/tests/integration/,
  modules/hub-ui/src/lib/api/, docs/, README.md. Requirements: AC-08.


Verification: `just lint`, `just check`, `just check-ui-api`, backend suite
925 passed/12 skipped; focused SQLite host+schema suite 19 passed/1 skipped;
PostgreSQL host suite 19 passed; SDK 27 passed and wheel/sdist built.
SQLite and PostgreSQL migration roundtrips match ORM metadata; single migration
head verified. SDK Docker metadata inclusion checked; container image not built.
