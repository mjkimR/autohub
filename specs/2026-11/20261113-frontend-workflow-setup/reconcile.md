---
reconcile_id: REC-frontend-workflow-setup
status: resolved
targets:
  - file: docs/development/README.md
    resolution: modified
  - file: docs/development/testing.md
    resolution: modified
  - file: docs/development/toolchain.md
    resolution: modified
---

# Frontend workflow reconciliation

## Impact and reflection

Only repository contributor tooling changes. Product capabilities, use cases, domain terms and architecture are unchanged. `ADR-sdd-development` keeps its development approach, selected bundles and approval policy.

| Target | Implementation agreement | Evidence |
| --- | --- | --- |
| Contributor README | Configured `just init` prepares locked Python/assets and frontend dependencies; fixing lint applies formatting and supported ESLint fixes. | `.devkit/config.toml`, `scripts/lint.sh`, actual successful `just init` and `just lint` |
| Testing guide | Describes isolated command execution coverage separately from real installed-tool verification. | `test_frontend_workflow.py`: 12 passing cases; full `just check` |
| Toolchain guide | All-module worktree setup and idempotent subsequent asset restoration replace the manual frontend prerequisite. | Real `just init`, subsequent `devkit sync --check`, pinned lifecycle inspection |

## Source feedback outcomes

- `FB-worktree-setup-skips-frontend-install`: resolved by the configured all-module setup. The locked Python/assets and frontend phases ran in actual setup, and controlled regressions verify each phase and failure propagation.
- `FB-lint-fix-skips-hub-ui-prettier`: resolved by formatting before the existing npm lint chain with its ESLint fix flag. Controlled regressions verify file changes and read-only preservation; actual full lint succeeds.

Both records receive a Disposition naming `SPEC-frontend-workflow-setup`. No other feedback is modified. No required accepted work is deferred; the unrelated CI manifest-reference check remains outside this spec.

## Reconcile verification

The medium-effort first reconcile-reviewer call is self-verified under the documented exception. All affected documents are the three identified developer guides, and each restates the exact changed contributor commands. No package/product capability behavior changes, cross-component contract interpretation or open decisions remain. The independent code reviewer already inspected these guide changes with the source range.

No native fresh-worktree creation or live deployment was executed. The configured command was executed directly; static inspection of the pinned lifecycle shows setup runs before its subsequent sync and holds no recursive sync lock. These are distinct from a live lifecycle test. Dependency manifests, lockfiles and generated assets are unchanged.

Entrypoint derivation returned zero pairs: all three guide targets are not entrypoint-bearing. No capability or use-case doorway was added.
