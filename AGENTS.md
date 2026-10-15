# Auto Hub: agent guide

Auto Hub automates GitHub PR work and CI observation on a scheduler foundation.
Backend: `modules/hub` (FastAPI). Frontend: `modules/hub-ui` (SvelteKit SPA).
Standalone pipeline SDK: `packages/sdk` (`autohub-sdk`, import `autohub_sdk`).
Keep SDK runtime dependencies independent of the backend and its database.
See [README](README.md) and [documentation guide](docs/README.md) for scope.

## Commands and verification

- Read [justfile](justfile) for targets, aliases, defaults, and scripts.
  Keep recipes thin; complex execution logic belongs in `scripts/`.
- Initialize the backend environment before using checks, even for frontend work.
- Run lint and verification builds before finishing: `just lint` and `just check`.
  `just lint-check` provides the read-only lint equivalent. Follow
  [development guidance](docs/development.md) for tests and PostgreSQL coverage.
- When API definitions change, regenerate the typed client with `just gen-ui-api`.
- For SDK changes, also run `just test-sdk` and `just build-sdk`; `just lint` and
  `just check` include SDK checks. See [SDK README](packages/sdk/README.md).

## Backend

- Follow `Router → UseCase → Service → Repository`.
- Use FastAPI dependencies with `Annotated[T, Depends(...)]`.
- Register tasks with `@task(name="namespace.name")` in
  `app/features/execution/tasks`, using Pydantic payloads. Import domain packages
  in its `domains/__init__.py` for discovery.

## Frontend

- Use Svelte 5 runes, SvelteKit 2 SPA, TypeScript, Tailwind v4, and shadcn-svelte.
  Style through `src/routes/layout.css` and its OKLCH tokens; themes use mode-watcher.
- Consume typed API resources through `$lib/api`; see the [UI README](modules/hub-ui/README.md).
- The shared size preset fails above 500 counted Svelte lines, 400 TypeScript lines,
  and 200 route lines. Split by responsibility first. Exceptions require an exact
  path, reason, and finite ceiling in `modules/hub-ui/eslint.config.js`.
  Never disable the rule or raise ceilings automatically. Read the installed
  app-common `ui/structure` guide; generated primitives are excluded, authored UI is not.

## Repository hygiene

- Never commit `.env` files or log credentials/PII.
- Commit messages are concise, imperative, and emoji-free.

## Documentation language

Use English for README/AGENTS files and technical, operational, or agent instructions.
Korean is for documents under `docs/` intended for the user's review, including
analysis, research, and their review indexes. Preserve localized examples, literal
UI labels, and the configured language of planning artifacts.

<!-- DEVKIT:START -->
## devkit

This repository installs agent assets with `devkit`. `.devkit/config.toml` selects
bundles; `.devkit/installation.json` records what is deployed.

- Before work that touches a bundle's assets, run `uv run devkit get-context <bundle>` once per bundle in the current agent context. Installed bundles: `advisory`, `app-common`, `devkit`.
- Entry skill `devkit-playbook`: find and run an operational playbook (explicit user invocation only).
- Never edit `.devkit/managed/` or projected agent files; change the source bundle or use `devkit override`.
- app-common packages: read the `app-common` skill before changing code that uses them; its architecture rules run in `devkit rules check`, and `devkit app guide list` lists the topics for this project.

This block is managed by `devkit sync`; edit outside the markers only.
<!-- DEVKIT:END -->
