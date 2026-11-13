# Impeccable session brief: <feature> (<SPEC-ID>)

Generic form of the brief that worked for `SPEC-hub-ui-color-system`. Replace every
`<...>` field; keep section order.

## Goal

<One paragraph: the approved direction to implement and its one-line rationale.>

## Framing (read-only sources; cite, do not copy)

- Binding contract: `specs/<YYYY-MM>/<YYYYMMDD-slug>/spec.md` (acceptance criteria,
  Screens drafts), `plan.md` (<sections>), `tasks.md` (<task IDs>). The spec is the
  design decision; Impeccable refines craft within it and does not re-choose direction.
- Product context: `<absolute path of the main checkout>/PRODUCT.md` (read-only; it is
  git-excluded, so a worktree does not contain it).
- OOUX: `docs/steering/glossary.md`, `docs/steering/ux-objects.md`,
  `docs/steering/visual-style.md`, the affected `docs/ux/` documents, `docs/usecases/`.
- Constraint: every documented use case stays achievable. List only user-stated
  constraints and explicit deferrals here; a task focus is not a prohibition.

## Working directory and base

- `<checkout path>`, branch `<branch>`, HEAD `<sha>`, clean status.
- Edit-list content hashes at base: `<path>` (<n> files are new).

## Edit list (only these files)

`<path to edit list>` (<n> paths = union of the tasks' `_Boundary` scopes).

## Unchanged

Data schema, backend (`modules/hub`), API client and generated types, dependencies
(`package.json`/lock), `docs/`, `specs/` (including task checkboxes; the coordinator
ticks them), README files, `PRODUCT.md`, `DESIGN.md`, ESLint config and size ceilings,
generated shadcn primitives other than <named exceptions>, index, HEAD and commits
(no `git add`/`commit`/`stash`/`checkout`).

## Context-file permission

<None | named files>. Do not write `PRODUCT.md`, `DESIGN.md`, `.impeccable/design.json`,
`.impeccable/config.json` or `.impeccable/surfaces/` unless named. Impeccable runtime
output under `.impeccable/` is allowed and must be reported.

## Precedence

The brief and spec win over Impeccable craft defaults (for example its border-left
guidance versus a spec-mandated attention rule); report each override.

## Commands

1. <command, e.g. colorize/layout> - implement <tasks> per spec, plan and tasks.
2. polish - on the changed views.
3. audit - on the changed views (manual detector; no hook installed).

Never run `live` or anything that disables sandbox or approvals. Run
`impeccable context --target modules/hub-ui/src/routes/layout.css`; repo-root
resolution misses the UI.

## Self-checks permitted

- Read-only checks from the repository root: `just lint-check`, `just check`, `just test-ui`.
- Screenshots: `HUB_UI_DIR=<checkout>/modules/hub-ui <scratch>/shots/run.sh after`
  (writes only to the scratch folder and ignored vite caches; compare with `out/before/`).
- Contrast: `<scratch>/contrast-check.py` with the token values under change.

## Stop condition

All commands finished with checks run, or a blocker (including any Impeccable question
needing the user: return it verbatim, never answer it).

## Expected return

Changed files (versus edit list), commands run with outcomes, audit findings (fixed
versus remaining), check results with counts, contrast results for key pairs,
after-screenshot paths and visible changes, session output under `.impeccable/`,
any out-of-list or out-of-spec change, degraded coverage, blockers and upstream
Impeccable contract surprises.
