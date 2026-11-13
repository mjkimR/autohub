---
id: CAP-SDD-runtime-isolation
title: Repository SDD runtime isolation and identity
summary: "Auto Hub evaluates repository workflow content with the devkit runtime pinned by the evaluated commit's uv.lock, installed per identity into a per-instance cache without giving repository code credentials or network. It preserves committed configuration and execution identity and bounds diagnostics."
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
  - modules/hub/app/features/project_management/sdd/runtime_cache.py
  - modules/hub/app/features/project_management/sdd/runtime_install.py
  - modules/hub/app/features/project_management/sdd/services.py
  - modules/hub/app/features/project_management/sdd/isolation.py
---

# [CAP-SDD-runtime-isolation] Repository SDD runtime isolation and identity

## 1. Summary

Each native evaluation runs devkit from the runtime that the evaluated commit's
root `uv.lock` pins (`ADR-repository-locked-runtime`). Hub installs that runtime
once per runtime identity into a per-instance cache. Git sources are fetched in
the Hub process; their builds run offline in the OS sandbox without credentials
(`ADR-offline-source-build`). Path sources inside the evaluated checkout are
captured by the Hub at selection, hashed into the runtime identity and built the
same way (`ADR-repository-path-sources`). Native evaluation reads exact PR commits in
disposable checkouts and runs repository workflow checks under OS isolation. The
committed config/receipt and effective workflow define the identity retained by
an admitted run; the runtime identity is recorded with it and follows the lock.

## 2. Scope & Boundary

- **In-Scope**: runtime selection from the evaluated commit's lock, runtime
  identity, cache installation and eviction, bundle preflight, managed-asset
  restore, committed configuration identity, workflow drift, CLI and build
  isolation, the runtime status probe and diagnostics.
- **Out-of-Scope**: `CAP-SDD-native-delivery` owns activity starts and proposal
  publication; `CAP-SDD-workflow-control` owns workflow actions and approval;
  `CAP-SDK-existing-pr-bridge` owns its separate evidence digest and PR claim.
  Serving-host setup and rollout settlement are operator procedures in the
  [runtime operations guide](../../operations/sdd-runtime.md).
- **Scope Excluded**: installing a repository's whole environment (only the locked
  group that declares `devkit-spec`, or the main dependencies); downloading Python
  interpreters; Git sources outside `https://github.com/`; path sources outside the
  checkout, through a symlink or with a marker; archive, URL or custom-index
  sources; editable installs (path sources install as built wheels); building
  registry sdists; a cache shared across instances
  or surviving restarts; a fallback server runtime for repositories without a
  devkit lock; unsandboxed evaluation; automatic repository initialization or
  upgrades. Reconsider these when a consumer needs another Git host, a private
  index or a registry sdist.

## 3. Business Rules & Policies

1. **Lock selection**: WHEN the first devkit command of a checkout scope runs, Hub
   MUST select the runtime from that checkout's root `pyproject.toml` and `uv.lock`:
   the first dependency group that declares `devkit-spec`, else the main
   dependencies. The checkout MUST be the base for Planning and Development start
   admission, the PR head for inspection, decisions and final lint, the milestone ref
   for previews and batches, the operator checkout for the SDK bridge and the
   default-branch head for runtime status.
   Check: [test_lock_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py), `test_group_selection_renders_only_the_devkit_group`, `test_main_dependencies_are_selected_without_a_group`; [test_lock_runtime.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_lock_runtime.py), `test_evaluation_uses_the_locked_runtime_and_records_its_identity`.
2. **Runtime identity**: Hub MUST derive the runtime identity from the selected
   group's `uv export` text, the content digest of each selected path source tree,
   the image interpreter's `major.minor` version and the build environment's lock
   digest, so that a lock change outside the group keeps the identity and a changed
   path source changes it.
   Check: [test_lock_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py), `test_unrelated_lock_change_keeps_the_identity_and_group_change_does_not`, `test_identity_covers_the_build_environment`, `test_path_source_identity_is_the_same_across_checkout_directories`, `test_path_source_content_and_executable_bit_change_the_identity`, `test_identity_without_path_sources_keeps_its_document`.
3. **Unlocked repository**: IF the commit has no readable root `pyproject.toml` or
   `uv.lock`, declares `devkit-spec` in no dependency group or main dependency, or
   its lock cannot be exported unchanged, THEN Hub MUST refuse with HTTP 422
   `SDD_RUNTIME_UNLOCKED` and start no install; no server profile or default image
   runtime is used instead.
   Check: [test_lock_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py), `test_repository_without_a_lock_is_refused`, `test_repository_whose_project_does_not_declare_devkit_spec_is_refused`, `test_symlinked_manifest_is_refused`; [test_lock_runtime.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_lock_runtime.py), `test_repository_without_a_devkit_lock_is_refused_through_checkout`.
4. **Unsupported sources**: IF the selected export contains an option line other
   than `-e ./<path>`, a path requirement that is not a `./<path>` inside the
   checkout whose components use only ASCII letters, digits, `.`, `_` and `-`, a
   path requirement that carries hashes or a marker or whose path the lock names
   as no `editable` or `directory` source, a URL or archive requirement, a Git
   source outside `https://github.com/` or without an exact 40-character revision,
   a registry requirement without SHA-256 hashes, a registry package whose lock
   source is not `https://pypi.org/simple`, or a path source whose directory is
   missing, reached through a symlink, lacks a regular `pyproject.toml`, contains a
   symlink or special file or exceeds the capture limits, THEN Hub MUST refuse with
   HTTP 422 `SDD_RUNTIME_SOURCE_UNSUPPORTED` before any fetch or download.
   Check: [test_lock_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py), `test_unsupported_sources_are_refused`, `test_registry_package_from_another_index_is_refused`, `test_unsafe_path_source_trees_are_refused`, `test_path_source_outside_the_checkout_is_refused_before_reading_it`, `test_path_source_size_is_bounded`.
5. **Python compatibility**: IF the root `requires-python` excludes the image
   interpreter's version, THEN Hub MUST refuse with HTTP 422
   `SDD_RUNTIME_PYTHON_UNSUPPORTED` before rendering the lock.
   Check: [test_lock_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py), `test_incompatible_python_is_refused_before_rendering`.
6. **Single-flight preparation**: WHILE no complete cache entry and no applicable
   failure marker exist for an identity, WHEN a devkit command needs that runtime,
   Hub MUST start at most one install per identity across worker processes and
   refuse the caller with HTTP 503 `SDD_RUNTIME_PREPARING`.
   Check: [test_runtime_cache.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_cache.py), `test_only_one_process_claims_an_identity`; [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_cold_cache_starts_one_install_and_reports_preparing`; [test_runtime_install.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py), `test_a_held_claim_skips_the_install`.
   A running native run that observes this refusal MUST keep its state and be inspected again on a later
   dispatcher tick until it has been preparing for 45 minutes, then block with a remediation reason; the SDK
   bridge MUST report only this refusal as the retryable `bridge-unavailable` and keep other evaluation
   refusals terminal; it surfaces a recorded install failure while the external trigger runs more often than the
   10-minute failure marker lasts.
   Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_preparing_runtime_keeps_the_run_and_retries_later`, `test_runtime_preparing_beyond_the_limit_blocks_the_run`; [test_contracts.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_contracts.py), `test_bridge_evidence_reports_a_preparing_runtime_as_retryable`, `test_bridge_worker_retries_preparing_and_fails_other_evaluation_errors`, `test_bridge_evidence_keeps_host_misconfiguration_terminal`.
7. **Caller-independent install**: WHEN a caller's deadline expires during an
   install, Hub MUST continue the install and publish the entry only by renaming
   a complete staging directory to the entry path.
   Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_caller_deadline_does_not_cancel_the_install`; [test_runtime_cache.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_cache.py), `test_publication_is_atomic_and_removes_stale_staging`, `test_an_existing_complete_entry_wins_publication`, `test_each_install_gets_a_fresh_unguessable_staging_path`; [test_runtime_install.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py), `test_install_publishes_a_complete_entry_with_an_identity_pin`.
8. **Hub-process fetch**: WHEN a runtime is installed, Hub MUST fetch its Git
   sources only in the Hub process with the project's GitHub connector token and
   keep that token out of every sandboxed step, `pin.json` and diagnostic.
   Check: [test_runtime_install.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py), `test_token_is_used_only_by_hub_process_fetches`.
9. **Sandboxed build steps**: WHEN Hub builds a locked Git or path source, installs the
   built wheels or probes the installed inventory, it MUST run that step in OS
   isolation without network, with a minimal environment and one writable
   directory (`work/` for builds, `.venv` for the wheel install and probe); builds
   MUST use the image's pinned build environment (`AUTOHUB_SDD_BUILD`) without build
   isolation.
   Check: [test_runtime_install.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py), `test_linux_sandbox_unshares_network_and_binds_one_writable_directory`, `test_sources_build_in_the_sandbox_offline_and_wheels_install_hashed`, `test_builds_write_only_work_and_the_wheel_install_runs_sandboxed`, `test_later_sandboxes_cannot_write_the_staging_root`, `test_probe_and_install_write_only_the_venv_and_read_the_hub_prefix`, `test_path_sources_are_staged_by_the_hub_and_built_in_the_sandbox`; [test_lock_runtime.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_lock_runtime.py), `test_source_build_hook_cannot_reach_the_network_or_credentials`, `test_path_source_runtime_installs_offline_through_the_sandbox`.
10. **Hub-authored pin**: WHEN an install finishes, Hub MUST write `pin.json` with
    the identity and interpreter prefix it computed itself, never values reported
    by the sandboxed probe.
    Check: [test_runtime_install.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py), `test_pin_prefix_comes_from_the_hub_not_the_probe`.
11. **Entry integrity**: IF a staged or cached directory is replaced or symlinked,
    or a cached `pin.json` names another provider or identity, THEN Hub MUST refuse
    to install or evaluate with it.
    Check: [test_runtime_install.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py), `test_symlinked_build_output_is_refused`, `test_a_swapped_venv_after_the_probe_fails_the_install`, `test_hub_never_acts_below_the_venv_after_a_late_swap`; [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_runtime_pin_must_name_its_own_entry`, `test_symlinked_entry_venv_is_refused`.
12. **Install failure back-off**: IF an install fails, THEN Hub MUST record its
    catalog code (`SDD_RUNTIME_SOURCE_UNAVAILABLE` for a refused fetch,
    `SDD_ISOLATION_UNAVAILABLE` when no isolation runner exists (rule 23), else
    `SDD_RUNTIME_INSTALL_FAILED`) for 10 minutes, scoped to a hash of the credential
    used, and refuse callers with that credential with HTTP 422 and that code
    without reinstalling.
    Check: [test_runtime_install.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py), `test_unreadable_source_records_a_failure_without_an_entry`, `test_malformed_inventory_records_a_failure`, `test_unexpected_errors_still_back_off`; [test_runtime_cache.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_cache.py), `test_failure_markers_expire`, `test_failure_markers_are_scoped_to_the_credential`; [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_recorded_failure_is_reported_without_reinstalling`.
13. **Leased eviction**: WHEN the cache exceeds `AUTOHUB_SDD_CACHE_BYTES`, Hub MUST
    remove least-recently-leased complete entries until the total fits, never an
    entry an evaluation holds leased.
    Check: [test_runtime_cache.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_cache.py), `test_eviction_skips_leased_entries_and_removes_least_recent`, `test_eviction_stops_when_only_leased_entries_remain`, `test_lease_never_waits_for_an_eviction`, `test_prune_removes_abandoned_staging_and_counts_active_staging`.
14. **Git without a runtime**: WHILE a checkout scope runs only `git-safe` commands,
    Hub MUST NOT resolve or install a runtime.
    Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_git_safe_never_resolves_a_runtime`; [test_lock_runtime.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_lock_runtime.py), `test_activity_branch_git_needs_no_runtime`.
15. **Bundle inventory**: WHEN a selected preset or committed receipt requires a
    bundle that no installed package of the locked runtime provides as a
    `devkit.bundles` entry point, Hub MUST refuse with HTTP 422
    `SDD_BUNDLES_MISSING` before sync.
    Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_bundles_missing_from_the_locked_runtime_refuse_before_sync`; [test_lock_runtime.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_lock_runtime.py), `test_bundle_without_a_locked_package_is_refused_before_sync`.
16. **Receipt required**: IF the committed installation receipt is missing, THEN Hub
    MUST refuse with `SDD_RECEIPT_MISSING` without initializing or syncing the
    repository.
    Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_missing_receipt_never_syncs_or_initializes`.
17. **Restore exception**: IF locked asset restoration reports `RECEIPT_STALE`, THEN
    Hub MUST attempt plain sync in the disposable checkout and retain a
    `RECEIPT_STALE` warning on successful regeneration.
    Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_stale_receipt_is_regenerated_best_effort_and_reported`, `test_stale_warning_names_the_locked_revision_when_recorded`.
18. **Restore failure**: IF plain regeneration fails or locked sync fails for another
    reason, THEN Hub MUST stop evaluation instead of treating the failure as a stale
    receipt warning.
    Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_failed_regeneration_after_a_stale_receipt_blocks`, `test_other_sync_failures_still_block`.
19. **Committed configuration**: WHEN restoration changes disposable managed assets,
    Hub MUST continue computing configuration identity from the config and receipt
    read before restoration.
    Check: [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_configuration_digest_uses_the_committed_receipt`.
20. **Identity continuation**: WHEN a later head of an admitted run resolves another
    runtime identity, Hub MUST continue evaluation and record the new
    `devkit-lock:<identity>` in the run snapshot.
    Check: [test_lock_runtime.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_lock_runtime.py), `test_changed_runtime_identity_continues_an_admitted_run`; [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_real_cli_reads_gate_and_rejects_changed_workflow`; [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_continued_run_records_the_new_runtime_identity`.
21. **Pinned execution**: IF the admitted effective workflow, policy or
    configuration changes without an authorized workflow transition, THEN Hub MUST
    refuse continuation under that changed contract.
    Check: [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_real_cli_reads_gate_and_rejects_changed_workflow`, `test_accepted_handoff_authorizes_only_the_selected_definition`; [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_policy_notices_are_projected_but_do_not_change_execution_authority`; [test_contracts.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_contracts.py), `test_workflow_pin_is_stable_across_checkouts_but_covers_effective_semantics`.
22. **Isolated commands**: WHEN running devkit or checkout-local safe Git, Hub MUST
    use OS isolation with the designated writable checkout, read-only access to the
    runtime entry and the Hub-computed interpreter prefix (devkit) or to system
    tools only (Git), no inherited host credentials and no network access. Native
    repository evaluation uses a disposable checkout; the SDK bridge uses its
    operator-provisioned checkout.
    Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_cli_drops_credentials_and_requires_isolation`, `test_devkit_sandbox_reads_the_hub_prefix_not_the_recorded_one`; [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_repository_python_rule_cannot_read_host_secret_or_use_network`.
23. **No isolation fallback**: IF no supported isolation runner is available, THEN
    Hub MUST refuse evaluation and runtime builds with `SDD_ISOLATION_UNAVAILABLE`
    instead of running repository code without isolation.
    Check: [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_no_unsandboxed_fallback`.
24. **Stale final lint**: IF final lint cannot load a rule recorded by a stale
    receipt, THEN Hub MUST block with the receipt remediation diagnostic without
    dispatching an agent attempt to repair that runtime failure.
    Check: [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_stale_receipt_lint_load_failure_pauses_with_the_diagnostic`; [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_stale_receipt_lint_failure_pauses_without_dispatching`.
25. **Sanitized failures**: WHEN a CLI command, runtime selection or runtime install
    fails, Hub MUST expose an allowlisted structured failure code and host-authored
    recovery text rather than repository stderr, Git output, URLs or free-form
    messages.
    Check: [test_diagnostics.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_diagnostics.py), `test_error_diagnostics_never_leak_upstream_values`, `test_host_failures_have_safe_actionable_diagnostics`; [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_json_diagnostic_never_leaks_repository_text`.
26. **Host probe**: WHEN runtime status is requested, Hub MUST start the image
    interpreter inside isolation, bounded to 30 seconds, without resolving or
    installing a repository runtime.
    Check: [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_runtime_status_probes_the_host_without_installing`, `test_host_probe_timeout_kills_the_sandboxed_process_group`; [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_runtime_status_starts_an_interpreter_inside_the_sandbox`.
27. **Project lock state**: WHERE the project has a GitHub repository and connector
    and the host probe passes, WHEN runtime status is requested, Hub MUST report the
    default-branch head's lock state as `ready`, `preparing` or `failed`, with its
    identity when selection succeeds.
    Check: [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_project_lock_state_is_reported_with_its_identity`, `test_runtime_endpoint_reports_both_failures_without_an_error`, `test_lock_status_reports_preparing_while_an_eviction_holds_the_entry`; [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_native_enrollment_requires_spec_and_readiness_is_read_only`.
28. **Notice projection**: WHEN isolated evaluation returns JSON notices, Hub MUST
    retain at most 20 distinct Hub-authored diagnostic records across that
    evaluation's nested reads, including successful commands and later failures.
    Check: [test_diagnostics.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_diagnostics.py), `test_notices_only_select_catalog_values_and_are_bounded`, `test_successful_subprocess_notices_are_collected_without_stderr`, `test_diagnostic_capture_is_task_local_and_nested_reads_share_one_evaluation`; [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_prior_warnings_are_retained_when_a_later_cli_call_fails`.
29. **Diagnostic identity boundary**: WHEN notices change without an effective
    policy or workflow change, Hub MUST exclude those notices from semantic
    execution identity rather than refuse continuation solely for diagnostic metadata.
    Check: [test_services.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_services.py), `test_policy_notices_are_projected_but_do_not_change_execution_authority`; [test_contracts.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_contracts.py), `test_workflow_notices_do_not_change_the_existing_semantic_hash`.
30. **Retired codes**: WHEN a retained record carries `RUNTIME_REVISION_MISMATCH`
    or `SDD_PROFILE_INVALID`, Hub MUST project that code's catalog text.
    Check: [test_diagnostics.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_diagnostics.py), `test_retired_revision_mismatch_warning_stays_readable`, `test_host_failures_have_safe_actionable_diagnostics`.
31. **Batch runtime identity**: WHEN batch basis evidence is captured, Hub MUST
    record `runtime` as only `provider`, `identity`, `python` and `revisions`, and
    exclude `uv.lock` from the `configuration` hashes.
    Check: [test_batch_evidence.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_batch_evidence.py), `test_basis_runtime_is_the_same_identity_across_cache_directories`; [test_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py), `test_runtime_identity_is_deterministic_and_pathless`.
32. **Path source capture**: WHEN the selected export contains an in-checkout
    path source (`./<path>`, or `-e ./<path>` for editable and workspace sources),
    Hub MUST read its tree in the Hub process at selection without following
    symlinks, skipping `.git`, `.venv` and `__pycache__` directories and within
    10,000 files and 32 MiB across the selection, and build only that captured
    copy, with no fetch or credential.
    Check: [test_lock_runtime.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py), `test_in_checkout_path_and_editable_sources_are_selected`, `test_devkit_spec_may_itself_be_a_path_source`, `test_workspace_members_inside_the_checkout_install_like_path_sources`, `test_caches_and_git_metadata_are_not_captured`; [test_runtime_install.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py), `test_path_only_runtime_needs_no_fetch_or_token`, `test_install_uses_the_content_captured_at_selection`.

## 4. Interfaces & Data Contracts

### Evaluated commit and selection

The evaluated commit (rule 1) is the base for Planning and Development start admission, the PR head for
inspection, decisions and final lint, the milestone ref for previews and batches,
the operator checkout for the SDK bridge and the default-branch head for runtime
status. Selection reads root `pyproject.toml` (at most 1 MiB) and `uv.lock` (at
most 8 MiB, no symlinks) and runs
`uv export --frozen --offline --no-header --no-annotate --no-emit-project --format requirements-txt`
with `--only-group <group>` or `--no-dev`. It builds and downloads nothing.
Each in-checkout path source line names its package through the lock's
`editable` or `directory` source of that path; `devkit-spec` itself may be one.
Selection captures the tree (rule 32) and holds the captured files for the
install, which may run after the disposable checkout is removed.

The runtime identity is the SHA-256 of the JSON document
`{"build": <build lock SHA-256 or "none">, "export": <export text>, "python": "<major>.<minor>"}`
with sorted keys; a selection with path sources adds
`"paths": {<checkout-relative path>: <tree digest>}`. The tree digest is the
SHA-256 of the sorted JSON list of `[<relative path>, "x" or "-", <content SHA-256>]`
per captured file, `x` marking the owner-executable bit. The snapshot CLI identity (`cli_version`) is
`devkit-lock:<identity>`. Workflow identity hashes semantic JSON while excluding
checkout/binding metadata. The run snapshot retains configuration digest, unit,
provider, CLI identity, workflow ID/hash and effective policy without diagnostic
notices. A continued run's snapshot takes the latest evaluated `cli_version`.

### Cache and install

| Variable | Default | Meaning |
| --- | --- | --- |
| `AUTOHUB_SDD_CACHE` | `/tmp/autohub-sdd-runtimes` | Per-instance cache root |
| `AUTOHUB_SDD_CACHE_BYTES` | `268435456` (256 MiB) | Eviction cap; a non-integer value uses the default |
| `AUTOHUB_SDD_BUILD` | `/opt/sdd-build` | Pinned build environment (hatchling) and its `uv.lock` |
| `AUTOHUB_SDD_PYTHON` | the Hub interpreter | Interpreter every runtime is created with |
| `AUTOHUB_UV` | `uv` on `PATH` | uv binary for export and install |

Hub reads neither `AUTOHUB_SDD_HOME` nor `AUTOHUB_SDD_PROFILES`.

An entry `<cache>/<identity>` is complete once its `pin.json` exists. Sibling files
are `<identity>.build` (exclusive install claim), `<identity>.lease` (shared
evaluation lease; its modification time orders eviction) and
`<identity>.failed-<scope>` (failure code for 10 minutes; `scope` is the first 16
hex characters of the credential's SHA-256). Staging directories are
`.staging-<identity>-<random>`; the next claim holder removes staging that a
crashed install left. Entries are content-addressed and shared by every project of
the instance that locks the same runtime.

Install steps, in a fresh staging directory:

1. Hub process: shallow `git fetch` of each distinct GitHub revision with the
   connector token into `work/src/`, and the captured files of each path source
   written to `work/src/path-<n>/` without a fetch or credential.
2. Hub process: `uv venv` with the image interpreter and
   `uv pip install --no-deps --only-binary :all: --require-hashes` of the registry
   wheels.
3. Sandbox writing `work/`: `uv build --wheel --offline --no-build-isolation` of
   each Git and path source with the `AUTOHUB_SDD_BUILD` interpreter.
4. Sandbox writing `.venv`: offline `uv pip install --no-index` of the built wheels.
5. Sandbox writing `.venv`: inventory probe of package versions and
   `devkit.bundles` entry points.
6. Hub process: write `pin.json`, remove `work/`, rename staging to the entry and
   evict over the cap.

The Hub-process Git fetches (step 1) run with the Hub environment plus the connector
credential header, with `HOME` set to the staging directory, system Git configuration,
terminal prompts and credential helpers disabled, and hooks and fsmonitor off. The uv and sandboxed install
subprocesses (steps 2-6) receive only `PATH`, `HOME`, `TMPDIR`, `LANG`, `NO_COLOR` and
uv settings (`UV_NO_CONFIG`, `UV_PYTHON_DOWNLOADS`, `UV_CACHE_DIR`, and
`UV_OFFLINE` for sandboxed builds and installs). `pin.json` holds `provider`
(`devkit-spec`), `identity`, `lock_sha256` (equal to `identity`), `group`,
`python`, `python_prefix`, `devkit*` package versions, `bundles` and Git
`revisions`; it holds no token, URL or timestamp.

### Refusal codes

| Code | HTTP | Category | Retry | Condition |
| --- | --- | --- | --- | --- |
| `SDD_RUNTIME_UNLOCKED` | 422 | repository | `after_fix` | Rule 3 |
| `SDD_RUNTIME_SOURCE_UNSUPPORTED` | 422 | repository | `after_fix` | Rule 4, including path sources over the rule 32 limits |
| `SDD_RUNTIME_PYTHON_UNSUPPORTED` | 422 | repository | `after_fix` | Rule 5 |
| `SDD_BUNDLES_MISSING` | 422 | repository | `after_fix` | Rule 15 |
| `SDD_RUNTIME_PREPARING` | 503 | runtime | `safe` | Rule 6, or an eviction holds the entry |
| `SDD_RUNTIME_SOURCE_UNAVAILABLE` | 422 | runtime | `after_fix` | Rule 12: the connector cannot read a locked Git source |
| `SDD_RUNTIME_INSTALL_FAILED` | 422 | runtime | `after_fix` | Rule 12, or a symlinked entry `.venv` |
| `SDD_RUNTIME_UNAVAILABLE` | 503 or 422 | runtime | `after_fix` | uv unavailable or no resolved runtime (503); inconsistent cached pin (422) |
| `SDD_ISOLATION_UNAVAILABLE` | 422 | runtime | `after_fix` | Rule 23 |

Readiness reports these as `ready: false` with the diagnostic; enrollment and other
requests return the HTTP status. A native run whose evaluation receives one of them
is blocked with the diagnostic, except `SDD_RUNTIME_PREPARING`, which keeps the
run's state until the 45-minute limit (rule 6). `SDD_ISOLATION_UNAVAILABLE` is not
in the diagnostic catalog: its HTTP error carries the code, while its diagnostic
row projects as `COMMAND_FAILED` with category `runtime`. `SDD_PROFILE_INVALID` and
`RUNTIME_REVISION_MISMATCH` remain in the catalog for retained records only.

### Runtime status

`GET /api/v1/projects/{project_id}/sdd/runtime` returns:

- Host probe: `ok`, `isolation` (`bubblewrap`, `sandbox-exec` or null) and
  `detail` (`Python <version>` or the probe failure).
- Constants: `profile` = `repository-lock`, `provider` = `devkit-spec`.
- Project lock state of the default-branch head: `state` (`ready`, `preparing`,
  `failed`, or null without a repository connection or when the host probe fails
  after the head was read; an unreadable head reports `failed` whatever the probe),
  `identity` and `lock_sha256` (both the identity), `bundles` and `revisions`
  (from the entry's pin when `ready`) and `lock_detail` (catalog text when
  `failed`, or a fixed Hub message when the head cannot be read or inspected).

The lock-state read may start a background install. A passing probe establishes
interpreter startup inside isolation on that serving host, not a repository
runtime, provider delivery or CI/merge success.

### Isolation

Linux evaluation uses bubblewrap with all namespaces unshared, including network;
it is the serving runner. macOS sandbox-exec cannot end detached processes a
sandboxed step leaves, so it is supported for local development only. devkit runs
as `<entry>/.venv/bin/python -I -B -m devkit_dist` reading the entry and the
interpreter prefix Hub computes, never the pin's `python_prefix`.

### Checkout and restore

Native evaluation requires regular `.devkit/config.toml` and `.devkit/installation.json`
files and an existing unit anchor. The fetch uses exact lowercase 40-character
head/base SHAs; `.devkit`, `specs` and `docs` symlinks are refused. Missing generated
assets are restored with `devkit sync --locked --format json`; the one permitted
stale fallback is `devkit sync --format json` in that disposable checkout. The
`RECEIPT_STALE` warning names the locked `devkit-spec` revision when the pin
records one.

Approved final lint invokes `devkit rules check --ci --base <base> --format json`
only when the inspected base is an ancestor of the head and the workflow requires
`lint-ci-clean`. Rule violations can become repair work; setup/execution failures
remain failures. A stale recorded-rule load failure has the special blocked result
above. Agents receive stale-receipt context without instructions to modify
`.devkit/` mid-run; the operator aligns the committed receipt and reenrolls.

### Diagnostics

Readiness and retained native run evidence expose `diagnostics` beside compatible legacy `warnings`. Each diagnostic contains `code`, `severity` (`error`, `warning`, `info`), `category` (`repository`, `runtime`, `decision`), `message`, `action`, `retry` (`after_fix`, `safe`, `never`) and `target_files`. The projection selects displayed values from Hub-owned mappings. Unknown notice codes become `DEVKIT_NOTICE`; unknown failures become `COMMAND_FAILED`. Repository messages, advisory fixes, arbitrary paths and stderr are not copied into these records. Guidance does not execute a command, retry work or grant authority.

Readiness failures caused by evaluated runtime/CLI errors retain safe diagnostics with `ready: false`. The run's blocked observation retains safe failure guidance. Notices remain separate from snapshot policy and workflow hashes. Historical warning records remain readable.

## 5. Source and Verification Boundary

The contract derives from [lock_runtime.py](../../../modules/hub/app/features/project_management/sdd/lock_runtime.py),
[runtime_cache.py](../../../modules/hub/app/features/project_management/sdd/runtime_cache.py),
[runtime_install.py](../../../modules/hub/app/features/project_management/sdd/runtime_install.py),
[runtime.py](../../../modules/hub/app/features/project_management/sdd/runtime.py),
[services.py](../../../modules/hub/app/features/project_management/sdd/services.py),
[usecases.py](../../../modules/hub/app/features/project_management/sdd/usecases.py),
[contracts.py](../../../modules/hub/app/features/project_management/sdd/contracts.py),
[diagnostics.py](../../../modules/hub/app/features/project_management/sdd/diagnostics.py),
[checkout.py](../../../modules/hub/app/features/project_management/sdd/checkout.py),
[isolation.py](../../../modules/hub/app/features/project_management/sdd/isolation.py)
and [batch_evidence.py](../../../modules/hub/app/features/project_management/sdd/batch_evidence.py).
The cited tests identify inspected evidence; this document does not record their
execution. Symlink rejection of checkout trees, the complete CLI diagnostic
allowlist, the absence of any emitter for the retired codes, the build-step
isolation refusal and the 1 MiB/8 MiB read limits are source-inspected boundaries.
The cold-install cost (11-18 seconds, a 29 MiB entry and a 153 MiB transient peak
at cpu=1, 1 GiB) is a recorded measurement in the `SPEC-repo-locked-sdd-runtime`
materials, not a CI check or a serving-host observation. Host setup, rollout and
recovery belong in the [runtime operations guide](../../operations/sdd-runtime.md).

## 6. Sequential admission identity

WHEN a batch prepares another activity, Hub MUST evaluate its current complete repository evidence through the same isolated native evaluator and compare the retained configuration/runtime identity (rule 31). Check: `modules/hub/tests/integration/features/project_management/sdd/test_batch_progression.py`.

WHEN committing a batch or preparing its external activity effect, Hub MUST re-read the selected remote base after policy evaluation and refuse a changed head before publishing. Check: `modules/hub/tests/integration/features/project_management/sdd/test_batches.py` and `modules/hub/tests/unit/features/project_management/sdd/test_batch_activities.py`.

`CAP-SDD-native-delivery` owns the limited accepted Planning, validated handoff and canonical edge-repair transitions. These authorize no unrelated configuration, workflow, policy, runtime or source drift. Admitted activities retain their own evaluated native identity; a batch never replaces the isolated runtime or silently reenrolls uncertain work.
