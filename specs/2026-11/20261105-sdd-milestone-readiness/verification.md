# Development verification

## Behavioral baseline

Base: `8f5003e54b8943ef80ca4c63ac92968482c3864e`. `git grep -n milestone-preview <base> -- modules/hub/app/features/project_management/sdd modules/hub-ui/src/lib/features/project-management/repositories` exited 1 with no matches. Source inspection confirms no preview endpoint or panel. No base checkout or performance timing was used.

After: the preview endpoint returns captured SHA, exact member/dependency observations and explicit completeness. The separate panel selects an eligible subset locally and ignores obsolete responses. Focused API/backend/real-runtime/UI fixtures verify this behavior. No numerical performance improvement is claimed.

## Executed checks

- `uv sync --no-active --locked --all-packages`: pass; locked environment initialized before checks.
- Initial `uv run devkit sync --check`: pass, exit 0, no output files.
- `just gen-ui-api`: pass after locked npm dependencies installed; the first attempt failed because the generator was not installed.
- `just check-ui-api`: pass.
- Existing activity unit suite: 25 passed.
- New preview unit/API/real-isolated catalog suites: 38 passed before final exact unresolved-ID strengthening; focused rerun recorded in final envelope.
- Owning repository UI suite: 24 passed, including stale-request and eligible-selection cases.
- Required `just test-sdd .cache/sdd-review` with `.cache/sdd-review-app-common`: 108 passed, 2 PostgreSQL-only lock-contention cases skipped. Both runtimes were provisioned from the declared pinned manifests. This executes real devkit and OS isolation; unit doubles are separate evidence.
- `just check`: pass for backend/SDK types, Svelte types and UI production build.
- `just lint-check`: backend, SDK and document phases passed; first UI pass found keyed-loop omissions, fixed before final rerun.

## Verification boundary

No deployed service, live GitHub operation, production rollout or browser walkthrough is claimed. No database locking or persistence semantics changed. PostgreSQL lock contention coverage is therefore not expanded by this feature. Repository snapshot and separately timestamped execution observations are not an atomic external snapshot.

## Review regression evidence

Round 1's actual upstream exception, nonanchor and missing PR evidence were reproduced by the independent review probe. Ignored replay of the reviewed `6a2885d` modules confirmed nonanchor `complete=True`, lost PR evidence and first-page-only pagination. The actual GitHubObservationError escaped the old path. Old-component replay produced Svelte `each_key_duplicate` for both duplicated milestone and member IDs. Probe harness setup errors were corrected before these observations; those setup failures are not red behavior evidence. No base checkout or source replacement was used.

Round 2's new historical flat-anchor defect failed the real-runtime `flat_proposal` fixture before its fix: only PROP-member appeared, omitting PROP-before. The corrected implementation mirrors the pinned devkit anchor predicate. Valid flat direct members remain unsupported for native start and visible for inspection; valid unfinished flat prerequisites remain held. The original nonanchor blueprint regression stays passing.

Latest complete owning SDD units plus new API/real-isolated catalog/Git fixtures: 153 passed. Full UI suite: 229 passed. Required full real isolated SDD suite after round-one fixes: 112 passed, 2 PostgreSQL-only lock-contention skips; later flat-anchor change is covered by the focused real-isolation fixture. Required lint/type/build checks passed after the first fix batch; final document/range verification follows reconciliation.

The two full isolated-suite skips are the PostgreSQL-only row-lock and publication/cancel contention fixtures, rather than missing runtime/profile coverage. Both declared runtimes were present. Earlier review/check summaries called these optional skips; this record supplies the precise boundary. No database locking semantics changed in this unit.

## Final PostgreSQL verification

`AUTOHUB_TEST_SDD_APP_COMMON="$PWD/.cache/sdd-review-app-common" just test-sdd-pg .cache/sdd-review` passed **115 tests with no skips**, using both provisioned locked profiles and real OS isolation. This includes both PostgreSQL contention cases and the final historical-flat-anchor fixture. The earlier SQLite skips are closed by this separate execution, without a locking implementation change. Final backend types, required read-only lint, document/hygiene rules, generated API freshness and committed-range whitespace/governance checks passed. Full UI remains 229 passed; complete owning SDD units plus new API/real Git/catalog fixtures remain 153 passed. Counts describe distinct runs and overlap; they are not summed.

## Host post-landing verification

The local no-ff integration landed at `a1580cd0376fb3ac7d8b2b3c6e9c7738f15cc061`, containing reviewed source `9b8b5ba7074012f267163ca9db82d508931691a5`. The saved premerge target was `01e1bd2251c526c3fe5107f3c2929931a073df77`. Its additional changes since the worker baseline concern test execution, fixtures, dependencies and approval settings. Integration used the retained base's `dev-integration=auto` policy after the user's approval of the same source and local cleanup effects. The development worktree, local branch and scope record were removed. No network publication occurred.

Fresh processes executed these checks against the landed main runtime:

- `uv sync --no-active --locked --all-packages`: passed.
- `uv run --no-active devkit sync --check`: passed with no changes.
- `uv run --no-active devkit generated check`: passed, one artifact checked and none stale.
- `just lint-check`: passed, including backend, SDK, UI and document/hygiene checks.
- `just check`: passed backend/SDK types, Svelte types and production UI build.
- `just check-ui-api`: passed.
- `just test-ui`: 229 passed across 40 files.
- `just test`: 1,284 passed and 62 skipped. The initial sandboxed run failed one local HTTP listener test because socket creation was denied; the complete rerun with the required host permission passed without source changes.
- `AUTOHUB_TEST_SDD_APP_COMMON="$PWD/.cache/sdd-app-common-v016" just test-sdd-pg .cache/sdd-v016`: 115 passed with no skips. Both runtime pin lock hashes matched the committed manifests. The initial sandboxed invocation could not access Docker and OS isolation; the permitted rerun passed without source changes.
- `uv run --no-active devkit rules check --ci --base 01e1bd2251c526c3fe5107f3c2929931a073df77`: passed 35 rules with no errors or warnings.
- `devkit workflow next` with the executed lint/merge evidence reports all stages complete.

The repository has no affected-test selector, so the complete backend and UI suites were used. PostgreSQL SDD coverage overlaps those tests and is reported separately. This record adds no deployment, live GitHub or rendered-browser evidence.
