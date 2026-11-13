# Impeccable app-uiux-improve pilot: restorable context, 2026-11-12/13

This record keeps what a later hub-ui UI session needs to repeat the Impeccable
workflow piloted through devkit's `app-uiux-improve` bundle. The pilot delivered
`SPEC-hub-ui-color-system` (merged at `c82bffb`). The approved color mechanism, its
rationale and the role rules are owned by `SPEC-hub-ui-color-system` and the
[visual style](../../../steering/visual-style.md) steering document; they are not
repeated here. The checks below were not rerun when this record was written.

## Attachments

| File | Purpose |
| --- | --- |
| [PRODUCT.md](attachments/PRODUCT.md) | Impeccable product context written by `init` (schema 1), verbatim |
| [brief-template.md](attachments/brief-template.md) | Generic Impeccable child-session brief |
| [shots/](attachments/shots/README.md) | Mocked-API Playwright screenshot harness: `run.sh`, `capture.mjs`, `fixtures.mjs`, `package.json`, `package-lock.json` |
| [contrast-check.py](attachments/contrast-check.py) | OKLCH to sRGB WCAG contrast check; its token table is the pilot's proposal and may differ from the merged `layout.css` |

No `DESIGN.md` or `.impeccable/` directory (design JSON, config or surfaces) was
created; on 2026-11-13 neither existed in the main checkout. Screenshot outputs,
`node_modules/`, logs and probe/discovery scripts were not retained.

## Restoring the product context

1. Copy `attachments/PRODUCT.md` to the repository root as `PRODUCT.md`.
2. Keep it local: confirm `.git/info/exclude` contains `/PRODUCT.md` and `/DESIGN.md`
   under `# Impeccable context files (local only)`. Do not commit it, even though
   Impeccable `init` step 6 recommends committing.
3. Linked worktrees do not receive excluded files. Pass the main checkout's absolute
   `PRODUCT.md` path read-only in the brief, or work in place with `--no-worktree`
   when the checkout is clean.

`PRODUCT.md` records "Autohub" as the canonical name while repository docs say
"Auto Hub"; that discrepancy was reported, not resolved.

## Re-running the workflow

- **Init relay.** Run `init` in a child session split in two: phase 1 scans and
  drafts the question round without writing; the coordinator pre-fills answers from
  the OOUX documents (glossary, UX object register, UX documents, use cases) and
  asks the user only the gaps; phase 2 resumes the same child with the answers and
  writes. The user answers every question; nobody answers on the user's behalf.
- **Skill loading.** A fresh Claude Code child could not load the Impeccable plugin
  skill through the Skill tool. Reading `SKILL.md` and `reference/*.md` from the
  plugin cache worked in both child runs.
- **Context target.** Run `impeccable context --target modules/hub-ui/src/routes/layout.css`.
  At the repository root it misses the monorepo UI; even with the target it still
  reported `hasVisualImplementation=false`.
- **Brief.** Use [the brief template](attachments/brief-template.md). Fields that
  mattered: binding spec/plan/tasks, read-only context paths, base HEAD with
  content hashes, an explicit edit list from the tasks' `_Boundary` union, an
  unchanged list, context-file permission, precedence of the spec over Impeccable
  craft defaults, the command sequence (implementation command, polish, audit),
  permitted self-checks, a stop condition that returns Impeccable questions
  verbatim, and the expected return. Accept the result by comparing `git status`
  against the edit list and the diff against the spec's acceptance criteria;
  an edit-list file can still carry out-of-spec changes.
- **Scope.** Non-goals carry only user-stated constraints and explicit deferrals.
  `PRODUCT.md` makes use-case coverage the only binding constraint; a "color first"
  focus is not a prohibition on layout or interaction changes.
- **Verification.** Inspect and verify the branch build locally with the mocked
  harness: capture `before`, apply the change, capture `after`. The deployed service
  shows only deployed code and is at most a baseline. The harness found an
  out-of-scope 390px dashboard overflow (416px scroll width).
- **Contrast.** Compute contrast from OKLCH values; designer-role estimates missed a
  light attention-on-card pair at 2.06:1 that the computed check caught.

## Deferred direction

- Shell lighting (a top attention rule and a Decisions navigation count) waits for
  a global pending-count source.
- The next approved spec is control density: replace hand-styled native `<select>`
  elements (about 29 Svelte files, roughly 40px tall) and explicit `h-10`/`h-11`
  controls (about 31 places) with a shared select at Input height, and align filter
  rows. Impeccable layout and polish were to be piloted again for it.
