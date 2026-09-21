# Auto Hub

Personal development automation connecting GitHub repositories and Codex cloud.
Auto Hub enrolls pull requests, dispatches implementation/fix requests, observes CI,
and manages retries, pause/resume, cancellation, and policy-controlled merges.
The scheduler, execution history, and connector management support these workflows.

Each connection represents one GitHub repository. Work is specified in PRs;
Codex cloud implements requests posted as `@codex` comments, and repository-owned
GitHub Actions perform verification. The workflow is:

`Open PR → Enroll and dispatch → Verify → Fix or merge`

Saved runs retain task snapshots and delivery history; dispatch reconciles comment
markers to avoid duplicate requests. See [delivery status](docs/delivery-status.md)
for implemented behavior and deferred work. [CI templates](templates/github-actions/README.md)
are manually installed starter files.

## Development

Python/FastAPI lives in `modules/hub`; Svelte/TypeScript in `modules/hub-ui`.
PostgreSQL is the standard database, with SQLite used for default testing.
[justfile](justfile) defines commands, aliases, and defaults; run `just --list`.

```sh
just init
just dev-run hub
just dev-run hub-ui
just lint
just check
just test
```

Initialize the Python environment even for frontend-only checks. Commands print
compact results and a `log:` path for full output. Backend initialization also
installs locked app-common skills through APM.

## Documentation

- [Documentation guide](docs/README.md): architecture, protocols, AI catalogs, and operator notices.
- [Development and operations](docs/development.md): checks, migrations, authentication, CI, and APM updates.
- [Connector encryption](modules/hub/README.md#connector-credential-encryption): key configuration and rotation constraints.
- [Frontend](modules/hub-ui/README.md): UI tooling and API generation.
- [Agent guide](AGENTS.md): code boundaries and required checks.
