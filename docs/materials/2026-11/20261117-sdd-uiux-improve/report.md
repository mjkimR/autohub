# SDD integration UI/UX improvement: mocked verification record, 2026-11-17

This record keeps the mocked-API capture harness and the verification scope of the SDD integration UI/UX
improvement run through devkit's `app-uiux-improve` bundle and Impeccable 4.8.2, outside the SDD workflow.
Behavior is owned by `CAP-SDD-native-delivery`, `UC-start-sdd-activity`, `UC-complete-sdd-workflow` and the
`docs/ux/sdd/` and `docs/ux/delivery/` documents; it is not repeated here.

## Delivered commits

| Commit | Scope |
| --- | --- |
| `063045c` | P1: start failure routing by error code, outcome beside Start, unit status, gate evidence and progress, readable read errors |
| `cd9e4dc` | UX documents for the P1 change |
| `5284d7e` | `CAP-SDD-native-delivery` rules 16-17, start refusal body, use case citations |
| `6fbd291` | P2: automatic claim evidence in one situation-titled card, Request details, actionable-only inbox attention, SDD run restart from its unit, display labels, separator wrapping, narrow composer |
| `679bee1` | UX documents for the P2 change |
| `5cb48a9` | Backend: last observed PR Draft and CI status on run reads (`CAP-PR-pull-request-delivery` rules 30-32); no UI uses it yet |

## Attachments

| File | Purpose |
| --- | --- |
| [shots/](attachments/shots/README.md) | Mocked-API Playwright harness with SDD fixtures: `run.sh`, `capture.mjs`, `fixtures.mjs`, `fixtures-sdd.mjs`, `package.json`, `package-lock.json` |

Screenshot outputs, `node_modules/` and logs were not retained. The harness extends the one in
[the Impeccable pilot record](../20261113-impeccable-uiux-pilot/pilot-context.md).

## Verification performed

Each round ran `just lint-check`, `just check` and `just test-ui` on the changed tree; all exited `0`
(630 tests after P1, 635 after P2). The harness captured the same shots and fixtures as `before`, `after` (P1)
and `after-p2`, in light and dark at 1440x900 and for selected shots at 390x844, with no unmocked requests or
page errors in `report.json`. Representative captures were inspected by eye: start success and refusal beside
Start, the gate evidence card, the claim card, the decision inbox and the narrow review dialog.
Backend change: `pytest` on the new pull observation tests, `test_timestamps.py` and the pipeline run unit tests
passed on `main`; PostgreSQL tests for the migration ran in the delegated worktree only.

## Coverage limits

- Every `/api` call was answered by fixtures; no backend, GitHub or provider was contacted. These are not
  end-to-end checks.
- Captures are viewport-sized; states below the fold were not captured.
- Impeccable's detector scans `.svelte` files with regex rules only, so its element rules did not run.
- No browser keyboard, screen-reader or live-overlay check was run.
- Impeccable `audit` results were not persisted, because `audit-storage` is not a command in 4.8.2.

## Deferred

- UI for `pull_observation` on the run page and the gate progress track.
- Draft recording during the implementation stage (today Draft is known only from `awaiting_ci`).
- The project start lock while a retained owner is bound to a live Run (`CAP-SDD-native-delivery` rule 13).
- SDD gate identity on decision inbox rows: `DecisionEntryRead` carries no activity or unit.
- Enrollment effort default (repository recommendation versus required effort).
- Browser keyboard, screen-reader and end-to-end checks against a real backend.
