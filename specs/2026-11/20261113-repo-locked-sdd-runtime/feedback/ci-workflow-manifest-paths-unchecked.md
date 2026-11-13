---
id: FB-ci-workflow-manifest-paths-unchecked
title: Local checks do not catch CI workflow steps that reference removed config manifests
scope: repo
kind: friction
category: other
target: .github/workflows/ci.yml
origin: agent
severity: workaround
recurring: false
status: resolved
created_at: 2026-11-13
---

# [FB-ci-workflow-manifest-paths-unchecked] Local checks do not catch CI workflow steps that reference removed config manifests

Verification coverage gap.

## 1. Friction / Question (friction, question)

- **Context**: A change removed `config/sdd-runtime-app-common` and updated `scripts/check-devkit.py`,
  `scripts/test-sdd.sh` and the image build.
- **Expectation**: `just lint`, `just check` and the test suites flag every remaining reference to the removed
  manifest before integration.
- **Actual**: All local checks passed while the `sdd-contract` job in `.github/workflows/ci.yml` still ran
  `just install-sdd .cache/sdd-app-common config/sdd-runtime-app-common` and set `AUTOHUB_TEST_SDD_APP_COMMON`; only
  a manual documentation pass found it.
- **Workaround (or Interpretation Chosen)**: Updated the job by hand after the Living Spec draft reported it.
- **Suggestion**: Add a check (for example in `check-devkit` or `docs-check`) that every `config/` path and `just`
  recipe argument referenced from `.github/workflows/*.yml` exists, or derive the CI provisioning steps from the same
  recipe the local `test-sdd` uses.


## Disposition

Resolved by `SPEC-ci-static-references` within the authorized direct static-reference scope. Backend lint invokes `just check-ci-references`, which checks actual root recipe/alias names and literal config arguments in simple YAML run commands. Missing recipe and deleted-path regressions fail before the fix and pass afterward; the final CI suite has 28 cases plus 12 neighboring contributor regressions. Current workflows report 23 supported commands, zero skips and zero errors. Full lint/check pass, and independent review reverified the unsupported-shell false-positive repair. Computed references and complex shell remain explicit unverified skips; no live Actions run is claimed.
