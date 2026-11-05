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
- Required `just test-sdd .cache/sdd-review` with `.cache/sdd-review-app-common`: 108 passed, 2 skipped optional cases. Both runtimes were provisioned from the declared pinned manifests. This executes real devkit and OS isolation; unit doubles are separate evidence.
- `just check`: pass for backend/SDK types, Svelte types and UI production build.
- `just lint-check`: backend, SDK and document phases passed; first UI pass found keyed-loop omissions, fixed before final rerun.

## Verification boundary

No deployed service, live GitHub operation, production rollout or browser walkthrough is claimed. No database locking or persistence semantics changed. PostgreSQL lock contention coverage is therefore not expanded by this feature. Repository snapshot and separately timestamped execution observations are not an atomic external snapshot.

## Review regression evidence

Round 1's actual upstream exception, nonanchor and missing PR evidence were reproduced by the independent review probe. Ignored replay of the reviewed `6a2885d` modules confirmed nonanchor `complete=True`, lost PR evidence and first-page-only pagination. The actual GitHubObservationError escaped the old path. Old-component replay produced Svelte `each_key_duplicate` for both duplicated milestone and member IDs. Probe harness setup errors were corrected before these observations; those setup failures are not red behavior evidence. No base checkout or source replacement was used.

Round 2's new historical flat-anchor defect failed the real-runtime `flat_proposal` fixture before its fix: only PROP-member appeared, omitting PROP-before. The corrected implementation mirrors the pinned devkit anchor predicate. Valid flat direct members remain unsupported for native start and visible for inspection; valid unfinished flat prerequisites remain held. The original nonanchor blueprint regression stays passing.

Latest complete owning SDD units plus new API/real-isolated catalog/Git fixtures: 153 passed. Full UI suite: 229 passed. Required full real isolated SDD suite after round-one fixes: 112 passed, 2 optional skips; later flat-anchor change is covered by the focused real-isolation fixture. Required lint/type/build checks passed after the first fix batch; final document/range verification follows reconciliation.
