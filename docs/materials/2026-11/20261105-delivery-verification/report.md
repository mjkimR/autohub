# devkit 0.1.6 local verification — 2026-11-05

This report retains the primary upgrade and subsequent compatibility follow-up
recorded on 2026-11-05. The checks were not rerun during documentation cleanup.
The two runs and their suites overlap; their counts are not additive.
See [delivery status](../../../operations/deployment-status.md) for the distinction
between local implementation and recorded production evidence.

## Reviewed inputs

The development environment and default/app-common SDD profiles used devkit 0.1.6
at monorepo commit `b151a10bb4ab9433c1dbaeb6c316917c959b6ba0`. Their manifests
and locks were aligned, and assets were synchronized in fresh environments.
The SDD profiles were provisioned at `.cache/sdd-v016` and
`.cache/sdd-app-common-v016`, preserving the previous installations.
The devkit-viewer artifact was rebuilt from the same commit and its npm integrity
was updated.

## Recorded checks

| Check | Primary upgrade | Compatibility follow-up |
| --- | --- | --- |
| Full backend, SQLite with reviewed SDD profiles | 1,218 passed / 17 skipped | 1,237 passed / 17 skipped |
| Required isolated SDD contracts, SQLite | 106 passed / 2 skipped | Not separately counted in the follow-up record |
| PostgreSQL SDD/SDK bridge contracts | 108 passed, no skips | 110 passed |
| Frontend | 210 passed | 215 passed |
| Standalone SDK | 27 passed; wheel and source distribution built | Not separately recorded |
| Focused backend, including pin mismatch and saved-answer compatibility | Not separately recorded | 62 passed |
| Real CLI metadata | Not separately recorded | 5 passed |

The primary SQLite SDD suite skipped two row-lock contention cases, which were
verified with PostgreSQL. Its coverage included acceptance, rejection, recovery,
handoff, profile selection and the SDK bridge. PostgreSQL also covered
publication/cancellation contention. Frontend checks exercised the rebuilt viewer
and four global/package roadmap paths, including their `_archive` directories.

The primary run passed `just lint`, `just check`, `just check-ui-api`,
`uv lock --check` in all three environments, `devkit status`,
`devkit sync --check`, local document-link checks and `git diff --check`.
The follow-up passed `just lint`, `just check`, `just check-ui-api`,
Ruff/Pyright checks for the new checker script, shell/YAML configuration checks
and document-link checks. Repository-wide `devkit rules check` recorded zero
errors and three existing HTTP-client warnings.

## Compatibility coverage

- Planning/Development starts, proposal acceptance and the Proposals UI follow the
  `incubation` to `adaptive-dev` rename. Saved runs using `incubation` retain the
  same lifecycle restrictions. A real-CLI regression checks the migration hint
  when the old configuration is rejected. Hub retains its existing CLI
  acceptance/publication/handoff contract and does not invoke devkit's composed
  acceptance/integration commands.
- `just test-sdd-pg` requires the provisioned runtime while running PostgreSQL SDD
  contracts. The `sdd-contract` CI job was configured to install both profiles and
  check SQLite and PostgreSQL, including publication/cancellation row-lock races.
- `just check-devkit` compares source/override/lock commits and versions across
  the three Python environments, viewer source-receipt provenance and SHA-256,
  and npm integrity offline. Backend lint and SDD CI run it before runtime
  installation; mismatches fail with `DEVKIT_PINS_INVALID`.
- Operator answers carry `by: user` into devkit publication. Saved operator
  answers gain that value when republished, and rejection answers record decision
  authority. Actual actor identifiers remain in existing Run/operation/commit
  records.
- Worker `scope_extensions` survive in Hub reports. Planning/Development approval
  screens display the added files, tasks, reasons and requirements, with the
  report expanded by default. Older reports remain readable, and existing
  approval, head and workflow checks remain in force.

## Limits

These records establish local verification only. They do not establish the
currently serving revision or an SDD baseline for Auto Hub's own development.
The primary upgrade did not include a production deployment, Docker image build
or live GitHub canary. The follow-up did not execute GitHub Actions remotely or
deploy to production. Actual provider replies, GitHub CI and merge behavior
remain separate live evidence.

Follow the [runtime transition procedure](../../../operations/sdd-runtime.md#assign-repositories)
when switching the serving host and settling active runs.
