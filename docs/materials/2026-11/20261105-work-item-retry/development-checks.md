# Work Item recovery verification

Input head: `f1e9693318ebf0181453142e75b98513fdbba4ff`.
Checks use controlled GitHub/provider fixtures. No live provider execution or deployment is asserted.

## Executed checks

- Required `just lint`, `just check` and `just check-ui-api`: passed. The checks include backend and SDK types, Svelte diagnostics and the production UI build.
- `just test-ui`: 218 tests passed in 38 files, including the recovery disclosure tests.
- Full affected SQLite Work Plan and PR-run integration suites with the recovery migration: 261 passed, 10 PostgreSQL-only skips.
- The same full affected suites on Docker/testcontainers PostgreSQL: 271 passed, no skips. This includes existing row-lock cases, distinct recovery requests and ordinary enrollment winning during recovery I/O.
- Expanded focused recovery SQLite suite: 29 passed, one PostgreSQL-only skip. The added cases cover linked Run revision, live leases, schedule, disabled project and catalog quota holds.
- Final expanded PostgreSQL recovery, ordinary-enrollment race and migration suite: 32 passed, no skips.
- Additive migration down/up preserves failed and successful legacy Items, leaves recovery history empty, retains uniqueness indexes and supports real recovery writes after upgrade.

## Before and after invariant measurement

Method: `test_three_item_chain_baseline_preserves_success_and_original_dependencies` runs one controlled three-Item fixture with the recovery command disabled and then enabled. It uses the same head and database; no baseline checkout or performance claim is involved.

Before explicit recovery, repeated ticks leave the second Item preparation_failed, its successor waiting and one Run belonging to the successful predecessor. After repair and explicit recovery, the second Item keeps its ID and obtains its first Run; the predecessor read projection is equal to its saved successful snapshot. The successor remains waiting until the recovered Item's original-target merge, then admits. Fresh delivery count is zero in this preparation-only measurement.

`test_terminal_recovery_keeps_run_epoch_and_commits_delivery` separately proves one retained terminal Run and unchanged epoch with one durable recovery delivery. `test_pushed_implementation_advances_ci_without_delivery` retains one prior delivery and adds no delivery while adopting current-head CI.

## Evidence boundary

Source inspection and executed checks are distinct. PostgreSQL results establish fixture locking behavior, not live GitHub behavior. Independent code and reconcile review records reside in the spec unit. The Host still verifies the eventual integrated head.


## Independent review correction evidence

Round 1 returned four P1 findings and one P2 disclosure finding. Each P1 received an executable regression before its production fix: the backend run reported four expected failures (last-Item Plan completion, held preparation edit fence, native-mode change during I/O and ordinary CI-fix silent allowance). The UI regression separately failed because the previous failure replaced the pending hold text.

After the batch fixes, all affected PostgreSQL integration/migration tests passed: 280 tests, no skips. Required lint, full type/build checks and API consistency passed. All 219 UI tests passed. Two further focused regressions reproduced definitive missing-base refusal remaining pending and native-mode changes during preparation holds; both were fixed within the same review batch.

Final focused PostgreSQL recovery, enrollment-race and migration tests: 37 passed, no skips. Final focused SQLite recovery and all PR-owner unit tests: 127 passed, one PostgreSQL-only skip. Final backend types: zero errors. These focused checks cover the final edge fixes; unchanged broad checks are retained rather than claimed as another execution.

## Host post-landing verification

Integration landed at `e5ffbf7f233ef9c9d811b9e2b94f6e72d66eb25a`.
Fresh locked setup and managed-asset checks passed. Generated-artifact verification
reported no stale artifact. `just lint-check`, `just check`, `just check-ui-api`
and `just test-ui` passed; the UI suite executed 219 tests. Full SQLite backend
verification executed 1,238 passing tests with 59 skips.

The PostgreSQL Work Plan, PR-run and migration selection initially reported
295 passed and one failure. The historical Work Plan migration roundtrip omitted
the recovery child migration before dropping its parent tables. The Host repaired
that test's downgrade/upgrade ordering and retained its complete metadata
comparison; production migration code was unchanged.

After the repair, both the Work Plan and recovery migration tests passed on
SQLite and PostgreSQL. `just test-pg modules/hub/tests/integration/migrations`
passed all 15 migration tests without skips. These reruns overlap the original
selection and are not additive. The remaining 295 PostgreSQL results are retained
because the repair changes only the historical migration test and import order.
The repaired test passed focused Ruff format/lint checks.
