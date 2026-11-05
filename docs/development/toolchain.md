# Updating dependencies and agent assets

Use pushed immutable source refs and review manifest/lock/artifact changes
together. Consumer environments use published packages rather than sibling
checkout paths or edited installed copies.

## app-common assets

The Python dependencies ship app-common's development bundle. `just skills` and
`just link-skills` synchronize installed assets and select the Python advisory
guide. The frontend ESLint package keeps its own source pin.

```sh
uv run devkit app update --ref <pushed-commit>
uv run devkit sync --check
```

Review the resulting manifests and `uv.lock`. Fresh environments use
`uv sync --locked --all-packages` followed by `uv run --no-sync devkit sync`.
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
