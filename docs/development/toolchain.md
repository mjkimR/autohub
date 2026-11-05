# Updating dependencies and agent assets

Use pushed immutable source refs and review manifest/lock/artifact changes
together. Consumer environments use published packages rather than sibling
checkout paths or edited installed copies.

## Selected agent assets

`ADR-sdd-development` records the development approach and catalog selection.

The root development group declares `devkit-spec` and the opt-in
`devkit-catalog` package at the reviewed immutable devkit commit. `devkit-spec`
brings the document system and harness; keep it as the single direct base
requirement. The explicit advisory dependency supports repository scripts.

`.devkit/config.toml` selects SDD and the following assets:

| Bundle/preset | Purpose |
| --- | --- |
| `spec:core`, `docs:core` | Development routing, workflow stages, support roles, document authoring and validation |
| `devkit:core`, `harness:core` | Asset consumption, rules, gates, worktrees and command execution |
| `advisory:core`, `advisory:python` | Agent-facing diagnostics and the Python advisory library |
| `app-common:all` | Existing backend/UI package guidance and architecture checks |
| `command-design:core` | Conditional guidance for justfile recipes, CLI commands and MCP tools |
| `maintenance:upkeep` | `drift-reconciliation` and `review-refactor` playbooks for bounded consistency and cleanup work |

Catalog installation exposes optional bundles; only selected presets deploy.
The catalog choices are limited to `command-design` and `maintenance:upkeep`.
Keep `adaptive-dev` unselected while using SDD. `cli-tool` imposes a CLI-specific
structure that does not fit the FastAPI application and independent SDK.
Research, UI/design exploration and response-style entries remain unselected
until requested. Weekly reporting and performance playbooks are outside the
selected maintenance preset.

Inspect deployment with `uv run devkit list` and `uv run devkit status`.
Selecting a playbook installs its procedure; run it only when the user invokes
or confirms it. Use `uv run devkit add <bundle>:<preset>` for approved additions
and review `.devkit/config.toml`, `.devkit/installation.json` and generated
guidance together.

These packages support changes to Auto Hub itself. The separate
`config/sdd-runtime*` manifests provision execution in connected repositories;
catalog selection in the contributor environment does not add catalog packages
to those runtimes.

## app-common assets

The Python dependencies ship app-common's development bundle. Use
`uv run devkit sync` to synchronize the bundles selected in `.devkit/config.toml`.
The frontend ESLint package keeps its own source pin.

```sh
uv run devkit app update --ref <pushed-commit>
uv run devkit sync --check
```

Review the resulting manifests and `uv.lock`. Fresh environments use
`uv sync --no-active --locked --all-packages` followed by
`uv run --no-active --no-sync devkit sync --locked` to restore committed assets.
New worktrees use the configured locked Python setup before devkit restores
their assets. Initialize frontend dependencies with `just init hub-ui` there
when the change needs UI checks.
Never edit `.devkit/managed/` or projected agent files directly.

## devkit and runtime profile updates

The backend development environment and both `config/sdd-runtime*` manifests are
reviewed against one devkit commit. Update root sources/override-dependencies and
both runtime profiles together; regenerate their locks from the intended refs.
Retain the backend's separate app-common pin when reviewing a toolchain update.

`just check-devkit` checks the three source/override/lock sets, release versions,
viewer provenance receipt, artifact SHA-256 and npm integrity offline. A mismatch
fails with `DEVKIT_PINS_INVALID`. Backend lint and SDD CI run it before runtime
provisioning.

1. Set the intended pushed refs explicitly in the manifests.
2. Refresh environments and locks from those refs.
3. Synchronize agent assets using matching installed packages and review generated receipts.
4. Rebuild vendored artifacts whose source changed, following the owning receipts below.
5. Run `just check-devkit`, `just lint`, `just check`, `just check-ui-api`, and the
   affected backend, SDK, frontend and isolated SDD contracts.

Keep previous reviewed runtime directories intact when provisioning a different
lock; [testing](testing.md#isolated-sdd-contracts) uses fresh destinations.
Switching a serving host and settling admitted runs is a separate
[operator procedure](../operations/sdd-runtime.md#assign-repositories).

## UI artifacts and generated declarations

- [devkit viewer receipt](../../modules/hub-ui/vendor/devkit-viewer.md) owns the
  viewer source identity and rebuild procedure.
- [API codegen receipt](../../modules/hub-ui/vendor/api-codegen.md) owns the
  generator source and vendored artifact.
- [UI contributor guide](../../modules/hub-ui/README.md) owns tag-based generated
  declarations. Use `just gen-ui-api` after a backend wire change and
  `just check-ui-api` to verify freshness.

The read-only viewer component's role is described by `ARCH-05-1-containers`;
repository browsing behavior belongs in `CAP-DOC-repository-viewer`.
