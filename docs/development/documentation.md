# Changing Auto Hub documentation

Read [the documentation guide](../README.md), relevant steering context and the
owning capability/use case before editing behavior. Keep authored prose in
English and preserve literal UI labels and localized examples.

## Authoring instructions

Follow devkit's `document-writing`, `living-spec-writing`, `contract-authoring`
and the applicable capability/use-case/architecture instruction and template.
The root development environment installs the `docs` bundle through
`devkit-spec`. Load its context before document work:

```sh
uv run devkit get-context docs
```

Read the instruction paths it returns and the steering documents whose summaries
apply to the change. Find documents with `uv run devkit docs list` and resolve
their IDs with `uv run devkit docs resolve <ID>`. Restore a missing environment from the
[locked toolchain](toolchain.md); do not substitute another repository's samples.

Put implemented guarantees in CAPs, actor goals/examples in UCs and structural
views in the appropriate arc42 chapter. Keep CAP/UC relationships reciprocal and
refer to ID-bearing documents by full ID. A code path or cited test identifies
evidence to inspect; it does not assert a fresh execution or production result.

`development/` covers work on Auto Hub itself. Put serving-host/client setup,
deployment and recovery procedures in `operations/`. Keep dated check evidence
in materials only when it supports an active compatibility/deployment claim.

## Validate the documents

Run the installed document rules against the working tree:

```sh
just docs-check
git diff --check
```

`just docs-check` checks `docs/`, root `AGENTS.md` and root `README.md` in the
linter and hygiene phases. Backend `just lint` and `just lint-check` include it,
so the existing backend CI invokes the same document checks.

Check metadata/IDs/summaries, referenced code paths, reciprocal relationships and
acceptance coverage for every extension. Update incoming links when a guide or
section moves. Inspect new untracked Markdown too; `git diff --check` alone does
not cover its whitespace. Execute the relevant product tests when contract
verification needs them, and report live-provider or database boundaries honestly.
