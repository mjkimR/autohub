# Changing Auto Hub documentation

Read [the documentation guide](../README.md), relevant steering context and the
owning capability/use case before editing behavior. Keep authored prose in
English and preserve literal UI labels and localized examples.

## Authoring instructions

Follow devkit's `document-writing`, `living-spec-writing`, `contract-authoring`
and the applicable capability/use-case/architecture instruction and template.
Use the repository's reviewed devkit revision. When the `docs` bundle is not
installed in the contributor environment, read these files from that revision's
`packages/devkit-docs/src/devkit_docs/bundles/docs/bundle/` source; do not infer a
format from an unrelated repository's document sample.

Put implemented guarantees in CAPs, actor goals/examples in UCs and structural
views in the appropriate arc42 chapter. Keep CAP/UC relationships reciprocal and
refer to ID-bearing documents by full ID. A code path or cited test identifies
evidence to inspect; it does not assert a fresh execution or production result.

`development/` covers work on Auto Hub itself. Put serving-host/client setup,
deployment and recovery procedures in `operations/`. Keep dated check evidence
in materials only when it supports an active compatibility/deployment claim.

## Validate the documents

The reviewed app-common SDD profile contains devkit-docs without adding it to the
backend's dependency set. After [provisioning that profile](testing.md#isolated-sdd-contracts),
run its actual documentation rules against the working tree:

```sh
AUTOHUB_DOC_RUNTIME="$PWD/.cache/sdd-review-app-common/.venv"
"$AUTOHUB_DOC_RUNTIME/bin/python" -I -B -m devkit_dist rules check docs AGENTS.md README.md --rules-dir "$AUTOHUB_DOC_RUNTIME/lib/python3.13/site-packages/devkit_docs/bundles/docs/bundle/rules"
"$AUTOHUB_DOC_RUNTIME/bin/python" -I -B -m devkit_dist rules check docs --phase hygiene --rules-dir "$AUTOHUB_DOC_RUNTIME/lib/python3.13/site-packages/devkit_docs/bundles/docs/bundle/rules"
git diff --check
```

Check metadata/IDs/summaries, referenced code paths, reciprocal relationships and
acceptance coverage for every extension. Update incoming links when a guide or
section moves. Inspect new untracked Markdown too; `git diff --check` alone does
not cover its whitespace. Execute the relevant product tests when contract
verification needs them, and report live-provider or database boundaries honestly.
