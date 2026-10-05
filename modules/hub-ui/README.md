# Hub UI (Svelte 5)

Frontend management console for **Autohub Scheduler Manager**, built with:

- **Framework**: Svelte 5 (Runes mode), SvelteKit 2 SPA mode
- **Bundler**: Vite 8
- **Styling**: Tailwind CSS v4, shadcn-svelte (bits-ui)
- **API Client**: openapi-typescript + openapi-fetch
- **Validation**: Native form constraints and backend validation errors

---

## Getting Started

### Development Server

Runs on port 5173 and proxies `/api` calls to the Python backend on `http://127.0.0.1:8389`:

```bash
just dev-run hub-ui
# Or from repo root:
npm --prefix modules/hub-ui run dev
```

### Static Type Check

Runs `svelte-check` against the TypeScript configuration:

```bash
just check hub-ui
# Or directly:
npm --prefix modules/hub-ui run check
```

### Code Formatting & Linting

```bash
just lint hub-ui
# Or fix formatting:
npm --prefix modules/hub-ui run format
```

### OpenAPI Client Generation

Regenerates tag-based declarations in `src/lib/api/generated/` from the FastAPI backend schema:

```bash
just gen-ui-api
```

## API contract generation

`npm run gen:api` exports the backend schema and uses the pinned
`@app-common/api-codegen` development package to generate declarations by tag.
`npm run check:api` verifies freshness without rewriting files, including added or
removed tags. Commit the generated directory after changing a backend contract.
Shared schemas live in `generated/common.d.ts`; `generated/index.d.ts` exports the
aggregate `paths` and `components`. Existing imports through `schema.d.ts` keep
working via its type re-export. Do not format or hand-edit generated declarations.

The package source commit and rebuild instructions are recorded in
[vendor/api-codegen.md](vendor/api-codegen.md); npm integrity is in the lockfile.

The exporter retains the backend's documentation tags unchanged. For generated
filenames, it normalizes the first tag to lowercase kebab case; secondary labels
(such as Users/Admin) stay within the primary domain. Reserved tags `common` and
`index` gain an `api-` prefix. Untagged endpoints fail export and must declare their
domain at the backend route.

Generation and freshness checks pass `--default-non-nullable` to retain the
previous openapi-typescript policy for properties with defaults.
