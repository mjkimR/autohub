# Backend tests

Use `unit`, `integration`, and `e2e` by execution boundary, not duration.
Within each tier mirror `app/` without the package prefix. For example,
`app/features/scheduling/schedule_configs/schemas.py` is covered under
`unit/features/scheduling/schedule_configs/`; repository/usecase/API tests share
that source owner under `integration/`. Tests of root scripts live under
`unit/scripts/`. Cross-feature fixtures stay at their nearest common parent.

- Unit uses doubles for database, HTTP and scheduler boundaries. Temporary input
  files are allowed. App routing/static serving is integration, even without a DB.
- Integration connects actual SQLite/PostgreSQL, repositories, usecases and
  in-process HTTP. Existing API suites previously called e2e belong here: clients
  use the ASGI app and external providers are stubbed.
- E2e is reserved for deployed/running process user journeys. There is currently
  no such suite; do not create an empty passing e2e command.

```sh
just test-unit
just test-integration
just test                 # all backend tests, unchanged default
just test-pg              # real PostgreSQL contracts; Docker required
just test modules/hub/tests/integration/features/scheduling
just test-ui              # all colocated frontend unit/component tests
```

Directory-derived markers make `-m unit` and `-m integration` consistent with
path selection and include new tests automatically. Unclassified Python tests
fail collection. Unit-only paths avoid importing integration app fixtures/model
registration. Shared app-testing-base plugin fixtures stay lazy and retain the
existing savepoint/real-commit contracts.

Frontend tests stay beside their source. Pure state/API-double tests are unit;
rendered component interactions in jsdom are integration. `npm --prefix
modules/hub-ui run test:unit` and `test:integration` select them; `test` runs both.
Use unit plus relevant integration during iteration, then the full suite before
completing broad changes. No changed-file dependency inference is assumed.
