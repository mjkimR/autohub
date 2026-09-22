# Auto Hub

Personal development automation connecting GitHub repositories and Codex cloud.
Auto Hub enrolls pull requests, dispatches implementation/fix requests, observes CI,
and manages retries, pause/resume, cancellation, and policy-controlled merges.
The scheduler, execution history, and connector management support these workflows.

Each connection represents one GitHub repository. Work can be specified in PRs;
Codex cloud implements requests posted as `@codex` comments, and repository-owned
GitHub Actions perform verification. The direct PR workflow is:

`Draft PR → Enroll and dispatch → Implement/fix → Mark ready (approval) → Verify → Merge`

A directly enrolled draft PR stays draft until the operator marks it ready for review. A non-draft
PR is approved for automatic merge once the configured CI passes (`auto_merge`
must be enabled); a PR enrolled already ready carries that approval. Returning it
to draft holds merging again. Hub never marks a PR ready on the operator's behalf.
Branch Protection Rules and required reviews are not used for this personal-repository
approval workflow. Existing GitHub rule-block handling is retained for compatibility.

[Work plans](docs/work-plans.md) accept task batches before PRs exist, with plan
dependencies and dependencies between items in the same plan. Registration requests
execution; eligible items create ready PRs and follow the project's merge policy.
Plan pause/revoke controls unstarted work. GitHub Issues mirror specifications and
history without controlling execution. This implementation awaits deployment and
live GitHub validation.

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
