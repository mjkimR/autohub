# Work Item recovery verification

Input head: `f1e9693318ebf0181453142e75b98513fdbba4ff`.
Checks use controlled GitHub/provider fixtures. No live provider execution or deployment is asserted.

## Executed checks

- Required `just lint`, `just check` and `just check-ui-api`: passed. The checks include backend and SDK types, Svelte diagnostics and the production UI build.
- `just test-ui`: 218 tests passed in 38 files, including the recovery disclosure tests.
- Full affected SQLite Work Plan and PR-run integration suites with the recovery migration: 261 passed, 10 PostgreSQL-only skips.
- The same full affected suites on Docker/testcontainers PostgreSQL: 271 passed, no skips. This includes existing row-lock cases, distinct recovery requests and ordinary enrollment winning during recovery I/O.
- Expanded focused recovery SQLite suite: 29 passed, one PostgreSQL-only skip. The added cases cover linked Run revision, live leases, schedule, disabled project and catalog quota holds.
- Additive migration down/up preserves failed and successful legacy Items, leaves recovery history empty, retains uniqueness indexes and supports real recovery writes after upgrade.

## Before and after invariant measurement

Method: `test_three_item_chain_baseline_preserves_success_and_original_dependencies` runs one controlled three-Item fixture with the recovery command disabled and then enabled. It uses the same head and database; no baseline checkout or performance claim is involved.

Before explicit recovery, repeated ticks leave the second Item preparation_failed, its successor waiting and one Run belonging to the successful predecessor. After repair and explicit recovery, the second Item keeps its ID and obtains its first Run; the predecessor read projection is equal to its saved successful snapshot. The successor remains waiting until the recovered Item's original-target merge, then admits. Fresh delivery count is zero in this preparation-only measurement.

`test_terminal_recovery_keeps_run_epoch_and_commits_delivery` separately proves one retained terminal Run and unchanged epoch with one durable recovery delivery. `test_pushed_implementation_advances_ci_without_delivery` retains one prior delivery and adds no delivery while adopting current-head CI.

## Evidence boundary

Source inspection and executed checks are distinct. PostgreSQL results establish fixture locking behavior, not live GitHub behavior. Independent code and reconcile review records reside in the spec unit. The Host still verifies the eventual integrated head.
