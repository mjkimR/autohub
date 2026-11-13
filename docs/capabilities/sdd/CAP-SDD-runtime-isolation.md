---
id: CAP-SDD-runtime-isolation
title: Repository SDD runtime isolation and identity
summary: "Auto Hub evaluates repository workflow content in a server-selected isolated runtime and preserves the committed configuration and execution identity across restoration. Bounded Hub-authored diagnostics distinguish repository, runtime and decision recovery without exposing arbitrary upstream text."
area: sdd
status: active
usecases:
  - UC-execute-sdd-batch
  - UC-start-sdd-activity
  - UC-decide-sdd-proposal
  - UC-complete-sdd-workflow
entrypoints:
  - modules/hub/app/features/project_management/sdd/runtime.py
  - modules/hub/app/features/project_management/sdd/lock_runtime.py
  - modules/hub/app/features/project_management/sdd/services.py
  - modules/hub/app/features/project_management/sdd/isolation.py
---

# [CAP-SDD-runtime-isolation] Repository SDD runtime isolation and identity

## 1. Summary

The host provisions reviewed runtime profiles independently of target repository
dependencies. Native evaluation reads exact PR commits in disposable checkouts and runs
repository workflow checks under OS isolation. The committed config/receipt,
runtime and effective workflow define the identity retained by an admitted run.

## 2. Scope & Boundary

- **In-Scope**: runtime/profile validation, bundle preflight, managed-asset restore,
  committed configuration identity, workflow drift, CLI isolation and diagnostics.
- **Out-of-Scope**: `CAP-SDD-native-delivery` owns activity starts and proposal
  publication; `CAP-SDD-workflow-control` owns workflow actions and approval;
  `CAP-SDK-existing-pr-bridge` owns its separate evidence digest and PR claim.
- **Scope Excluded**: installation of target dependencies during requests,
  unsandboxed evaluation, automatic repository initialization/upgrades and silent
  runtime replacement for admitted work. Host provisioning is an operator procedure.

## 3. Business Rules & Policies

1. **Runtime lock identity**: IF the runtime pin is absent, unreadable, lacks its
   provider/lock identity, names another provider or disagrees with its runtime lock
   SHA-256, THEN Hub MUST refuse
   evaluation with `SDD_RUNTIME_UNAVAILABLE`.
   Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_runtime_pin_detects_changed_lock`.
2. **Server mapping validation**: IF server profile/repository mappings are invalid,
   THEN Hub MUST refuse with `SDD_PROFILE_INVALID` rather than silently choose a
   fallback profile.
   Check: [test_profiles.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py), `test_invalid_server_mapping_never_falls_back`.
3. **Evaluation-local selection**: WHEN evaluating mapped repositories concurrently,
   Hub MUST retain each operation's selected runtime and reset that selection when
   its scope ends, including after failure.
   Check: [test_profiles.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py), `test_repository_profiles_are_task_local_and_reset_after_failure`.
4. **Bundle inventory**: WHERE the runtime pin records bundle inventory, WHEN a
   selected preset or committed receipt requires an unavailable bundle, Hub MUST
   refuse with `SDD_BUNDLES_MISSING` before sync or dependency installation.
   Check: [test_profiles.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py), `test_bundle_preflight_uses_selection_and_receipt_without_running_project_code`.
5. **Receipt required**: IF the committed installation receipt is missing, THEN Hub
   MUST refuse with `SDD_RECEIPT_MISSING` without initializing or syncing the repository.
   Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_missing_receipt_never_syncs_or_initializes`.
6. **Restore exception**: IF locked asset restoration reports `RECEIPT_STALE`, THEN
   Hub MUST attempt plain sync in the disposable checkout and retain a
   `RECEIPT_STALE` warning on successful regeneration.
   Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_stale_receipt_is_regenerated_best_effort_and_reported`.
7. **Restore failure**: IF plain regeneration fails or locked sync fails for another
   reason, THEN Hub MUST stop evaluation instead of treating the failure as a stale
   receipt warning.
   Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_failed_regeneration_after_a_stale_receipt_blocks`, `test_other_sync_failures_still_block`.
8. **Committed configuration**: WHEN restoration changes disposable managed assets,
   Hub MUST continue computing configuration identity from the config and receipt
   read before restoration.
   Check: [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_configuration_digest_uses_the_committed_receipt`.
9. **Pinned execution**: IF runtime identity or the admitted effective workflow,
   policy or configuration changes without an authorized workflow transition, THEN
   Hub MUST refuse continuation under that changed contract.
   Check: [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_real_cli_reads_gate_and_rejects_changed_version`, `test_accepted_handoff_authorizes_only_the_selected_definition`; [test_profiles.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py), `test_workflow_pin_is_stable_across_checkouts_but_covers_effective_semantics`.
10. **Revision parity warning**: WHEN a readable root lock provides a compared
    package's exact Git revision different from the runtime pin, Hub MUST report
    `RUNTIME_REVISION_MISMATCH` without exposing its source URL or credentials.
    Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_revision_mismatch_is_a_warning_without_repository_text`, `test_revision_parity_is_silent_without_an_exact_signal`.
11. **Isolated commands**: WHEN running devkit or checkout-local safe Git, Hub MUST
    use OS isolation with the designated writable checkout, read-only runtime/tools,
    no inherited host credentials and no network access. Native repository
    evaluation uses a disposable checkout; the SDK bridge uses its operator-provisioned checkout.
    Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_cli_drops_credentials_and_requires_isolation`; [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_repository_python_rule_cannot_read_host_secret_or_use_network`.
12. **No isolation fallback**: IF no supported isolation runner is available, THEN
    Hub MUST refuse with `SDD_ISOLATION_UNAVAILABLE` instead of running repository
    code without isolation.
    Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_no_unsandboxed_fallback`.
13. **Stale final lint**: IF final lint cannot load a rule recorded by a stale
    receipt, THEN Hub MUST block with the receipt remediation diagnostic without
    dispatching an agent attempt to repair that runtime failure.
    Check: [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_stale_receipt_lint_load_failure_pauses_with_the_diagnostic`; [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_stale_receipt_lint_failure_pauses_without_dispatching`.
14. **Sanitized CLI failure**: WHEN a CLI command fails, Hub MUST expose an allowlisted
    structured failure code and host-authored recovery text rather than repository
    stderr or free-form messages.
    Check: [test_diagnostics.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_diagnostics.py), `test_error_diagnostics_never_leak_upstream_values` and `test_host_failures_have_safe_actionable_diagnostics`.
15. **Serving-host probe**: WHEN runtime status is requested, Hub MUST probe the
    selected runtime inside isolation without requiring a PR or starting a run.
    Check: [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_runtime_status_starts_devkit_inside_the_sandbox`.

16. **Notice projection**: WHEN isolated evaluation returns JSON notices, Hub MUST retain at most 20 distinct Hub-authored diagnostic records across that evaluation's nested reads, including successful commands and later failures.
    Check: [test_diagnostics.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_diagnostics.py), `test_notices_only_select_catalog_values_and_are_bounded`, `test_successful_subprocess_notices_are_collected_without_stderr`, `test_diagnostic_capture_is_task_local_and_nested_reads_share_one_evaluation`; [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_prior_warnings_are_retained_when_a_later_cli_call_fails`.
17. **Diagnostic identity boundary**: WHEN notices change without an effective policy or workflow change, Hub MUST exclude those notices from semantic execution identity rather than refuse continuation solely for diagnostic metadata.
    Check: [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_policy_notices_are_projected_but_do_not_change_execution_authority`; [test_profiles.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py).

## 4. Interfaces & Data Contracts

`GET /api/v1/projects/{project_id}/sdd/runtime` returns `ok`, `profile`, `bundles`,
`provider`, `lock_sha256`, `revisions`, `isolation` and optional `detail`. Runtime
or isolation probe failure can be represented by `ok: false`; invalid profile
configuration is an HTTP 422 refusal. A passing probe establishes CLI startup on
that serving host, not provider delivery or CI/merge success.

`AUTOHUB_SDD_HOME` selects the default runtime, default `/opt/sdd`.
`AUTOHUB_SDD_PROFILES` maps profile names to absolute directories and repository
names to a profile. Repository matching is case-insensitive. Unmapped repositories
use the default; invalid mappings never silently fall back. Profile selection is
shared by inspection, activity creation, decisions and SDK evidence evaluation.

The pin stores `provider: devkit-spec`, `lock_sha256`, package versions, Python
prefix, available bundles and, when recorded, exact Git revisions. CLI identity
is `devkit-spec:<lock_sha256>`. Workflow identity hashes semantic JSON while
excluding checkout/binding metadata. The run snapshot retains configuration digest,
unit, provider, CLI identity, workflow ID/hash and effective policy without diagnostic notices.

Native evaluation requires regular `.devkit/config.toml` and `.devkit/installation.json`
files and an existing unit anchor. The fetch uses exact lowercase 40-character
head/base SHAs; `.devkit`, `specs` and `docs` symlinks are refused. Missing generated
assets are restored with `devkit sync --locked --format json`; the one permitted
stale fallback is `devkit sync --format json` in that disposable checkout.
No repository dependency installation occurs during evaluation.

Approved final lint invokes `devkit rules check --ci --base <base> --format json`
only when the inspected base is an ancestor of the head and the workflow requires
`lint-ci-clean`. Rule violations can become repair work; setup/execution failures
remain failures. A stale recorded-rule load failure has the special blocked result
above. Agents receive stale-receipt context without instructions to modify
`.devkit/` mid-run; the operator aligns the committed receipt and reenrolls.

Revision parity is best effort over exact locked revisions of the seven compared
devkit packages. A missing, symlinked, malformed or larger-than-8-MiB root `uv.lock`,
an old pin without revisions or a nonexact reference supplies no mismatch signal.
No warning is proof that the agent's installed runtime matches Hub.

Readiness and retained native run evidence expose `diagnostics` beside compatible legacy `warnings`. Each diagnostic contains `code`, `severity` (`error`, `warning`, `info`), `category` (`repository`, `runtime`, `decision`), `message`, `action`, `retry` (`after_fix`, `safe`, `never`) and `target_files`. The projection selects displayed values from Hub-owned mappings. Unknown notice codes become `DEVKIT_NOTICE`; unknown failures become `COMMAND_FAILED`. Repository messages, advisory fixes, arbitrary paths and stderr are not copied into these records. Guidance does not execute a command, retry work or grant authority.

Readiness failures caused by evaluated runtime/CLI errors retain safe diagnostics with `ready: false`. The run's blocked observation retains safe failure guidance. Notices remain separate from snapshot policy and workflow hashes. Historical warning records remain readable.

## 5. Source and Verification Boundary

The contract derives from [runtime.py](../../../modules/hub/app/features/project_management/sdd/runtime.py),
[profiles.py](../../../modules/hub/app/features/project_management/sdd/lock_runtime.py),
[services.py](../../../modules/hub/app/features/project_management/sdd/services.py),
[contracts.py](../../../modules/hub/app/features/project_management/sdd/contracts.py),
[diagnostics.py](../../../modules/hub/app/features/project_management/sdd/diagnostics.py),
[checkout.py](../../../modules/hub/app/features/project_management/sdd/checkout.py)
and [isolation.py](../../../modules/hub/app/features/project_management/sdd/isolation.py).
The cited tests identify inspected evidence. Symlink rejection and the complete
CLI diagnostic allowlist are source-inspected boundaries, not a claim that each
case has a separately executed regression test. Provisioning and host recovery
belong in the [runtime operations guide](../../operations/sdd-runtime.md).

## 6. Sequential admission identity

WHEN a batch prepares another activity, Hub MUST evaluate its current complete repository evidence through the same isolated native evaluator and compare the retained configuration/runtime identity. Check: `modules/hub/tests/integration/features/project_management/sdd/test_batch_progression.py`.

WHEN committing a batch or preparing its external activity effect, Hub MUST re-read the selected remote base after policy evaluation and refuse a changed head before publishing. Check: `modules/hub/tests/integration/features/project_management/sdd/test_batches.py` and `modules/hub/tests/unit/features/project_management/sdd/test_batch_activities.py`.

`CAP-SDD-native-delivery` owns the limited accepted Planning, validated handoff and canonical edge-repair transitions. These authorize no unrelated configuration, workflow, policy, runtime or source drift. Admitted activities retain their own evaluated native identity; a batch never replaces the isolated runtime or silently reenrolls uncertain work.
