---
reconcile_id: REC-ci-static-references
status: resolved
targets:
  - file: docs/development/README.md
    resolution: modified
  - file: docs/development/testing.md
    resolution: modified
---

# CI static reference reconciliation

## Impact and reflection

Only root contributor tooling and its own developer guidance change. Product capabilities, use cases, storage, architecture, domain terminology and approval policy are unchanged. No ADR or general governance rule is introduced.

| Target | Agreement with implementation | Enforcing evidence |
| --- | --- | --- |
| Contributor README | Lists the thin check-ci-references recipe and its backend lint integration. | justfile, check-backend.sh, actual checker success and lint-hook failure propagation test |
| Testing guide | Defines direct literal recipe/alias and config argument validation, literal directory precedence, nonexecution, failure diagnostics and explicit unverified syntax skips. | 28 CI command regressions; actual workflow 23 supported commands, zero skips and errors |

The medium-effort reconcile check uses self-verification under the documented exception. Both affected documents are identified above and restate the root tooling behavior reviewed independently with the source. No package/product capability contract or cross-component interpretation changes. The guide boundary agrees with the conservative whole-run handling independently reverified after P2 repair.

## Source feedback outcome

`FB-ci-workflow-manifest-paths-unchecked` is resolved within the authorized static-reference scope. Local default lint now checks missing directly named recipes and config arguments before backend source checks. Its Disposition names `SPEC-ci-static-references`, the permanent missing-reference regressions, actual current workflow inspection and required lint/check execution. No unrelated feedback is modified.

Unsupported dynamic/compound forms remain the explicit Non-Goal, not deferred required work. No additional accepted product work is deferred. Actual GitHub Actions or live-provider execution is not claimed; the checker deliberately does not execute workflow commands or recipes. Host integrated-head verification remains pending.
