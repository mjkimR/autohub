# hub-ui screenshot harness (mocked API)

Captures hub-ui pages in light and dark themes from a local `vite dev` server, with
every API call answered by fixtures. Use it to compare a branch build before and
after a UI change; it never contacts a real backend or the deployed service.

## Restore and run

1. Copy this directory to a scratch location outside the repository, for example
   `<scratch>/shots/`, and make `run.sh` executable.
2. Install the hub-ui dependencies in the checkout under test (`modules/hub-ui/node_modules`).
3. Run `HUB_UI_DIR=<autohub checkout>/modules/hub-ui <scratch>/shots/run.sh before`,
   make the change, then run it again with `after`.

`run.sh` runs `npm ci` on first use (Playwright 1.63.0 from `package-lock.json`).
If the browser is missing, run `npx playwright install chromium` in the restored
directory; the pilot used the cached chromium-1243 build that matches 1.63.0.
The pilot ran Node 24.18 (set `NODE_BIN` to its `bin` directory if `node` on
`PATH` differs); Playwright 1.63.0 requires Node 20 or later.

Output: `out/<label>/<page>-<theme>.png` (viewport 1440x900, or 390x844 for
`*-narrow`), `out/<label>/full/` (full-page variants) and `out/<label>/report.json`
(unmocked requests, page errors, theme mismatches, horizontal overflow).

## How it works

- `run.sh` starts `vite dev` from `HUB_UI_DIR` on port 5199 (`PORT` overrides) with
  `--configLoader runner`, so no `vite.config.ts.timestamp-*` file is written, and
  `AUTO_HUB_SERVER=http://127.0.0.1:9`, a closed port the dev proxy can never reach.
  It runs `capture.mjs` and stops the server on exit. Only the ignored `.svelte-kit/`
  and `node_modules/.vite` caches change in the checkout.
- `capture.mjs` intercepts every same-origin `/api/*` request with `fixtures.mjs`,
  aborts any cross-origin request, freezes the clock at 2026-11-12T09:30Z and uses
  UTC, `en-US` and reduced motion.
- Auth: `POST /api/v1/auth/browser/refresh` returns a mock access token, so the
  layout's session restore succeeds; `/api/v1/users/me` returns a superadmin, so the
  admin navigation is visible.
- Theme: an init script sets `localStorage['mode-watcher-mode']` with a matching
  `colorScheme`; the harness verifies the `dark` class on `<html>`.

## Extending

Add a page to `pages` in `capture.mjs`, run once and read `report.json.unmocked`,
then add handlers in `fixtures.mjs` using the shapes in
`modules/hub-ui/src/lib/api/generated/*.d.ts`. Fixtures match the API at commit
`f17aeda`; `scenario.observation` selects a `pull_observation` case (`none`, `draft-waiting`,
`ready-failed`, `ready-passed`, `earlier-head`). Update shapes after API changes. The `ready`
texts and actions in `capture.mjs` match the hub-ui copy at `f17aeda`; a copy change that a
shot waits for needs its `ready` text updated.

## SDD extension

- `fixtures-sdd.mjs`: SDD project repository (virtual tree/blobs for docs, proposals, specs, roadmap),
  five SDD runs (gate question open, answer saved/resume pending, implementing, failed, completed),
  questions, attempts, decision entries, owed-item counts, claims and start outcomes.
- `capture.mjs`: per-shot `scenario` (`fail`/`hang` regexes on `METHOD /path?query`, `override`,
  `start`, `claim`, `sddRuns`), `actions` (clicks), `ready` text. Writes `report.json`
  (global + per-shot unmocked/errors) and `index.json` (file -> URL, viewport, scenario).
- Default run captures SDD shots only; `SUITE=all` adds the original pages; `ONLY=a,b` filters by name.
- `crypto.randomUUID` is made deterministic per page so request ids in screenshots are stable.
