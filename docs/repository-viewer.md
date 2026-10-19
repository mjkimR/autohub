# Repository Viewer and SDD Projects

Set `project_type` according to the kind of project (`general` / `sdd`).
The built-in repository viewer adapts its screen to the project type.

## Project modes

| Mode (`project_type`) | Description |
| --- | --- |
| `general` | Default Git browser (directory tree, file contents, README preview) |
| `sdd` | Spec-driven project viewer for `devkit-spec` repositories (Living Spec reading, Proposals and Specs indexes, milestone roadmap, file explorer), the native SDD run panel, and the Git browser |

Choose `Project Type` in the project settings or when registering a new project.
See [Native SDD runtime](development.md#native-sdd-runtime) for the runtime the
`sdd` mode executes with.

## Native viewer

The viewer is the Svelte component `SddViewer` of the `devkit-viewer` library, which
devkit owns. autohub compiles it into its own build from the tarball committed under
`modules/hub-ui/vendor/` ([pinned artifact](../modules/hub-ui/vendor/devkit-viewer.md));
it needs no runtime bundle download, deployment-time plugin installation, or
`repository-viewers.local.json` configuration file. Change the viewer in devkit, then
refresh the tarball; the Git browser, the SDD execution panel and the Proposals panel
stay in autohub.

- `sdd` projects open **Sdd View** by default and can switch to **Git Browser**.
- **Sdd View** has the tabs `문서 읽기` (the `docs/` Living Spec grouped by chapter),
  `Proposals` (`docs/proposals/PROP-*/` bundles), `Specs` (`specs/` task bundles)
  (the Proposals panel above the viewer starts and decides proposals; see
  [run decisions](run-decisions.md#proposals-panel)),
  `로드맵` (`docs/roadmap/MS-*.md` milestones by status, `depends_on` readiness and
  member proposals and specs) and `파일 탐색` (file explorer), with search and status
  filters. The roadmap reads the repository's default branch: autohub's data source
  lists no branches, so members on `plan-` and `dev-` branches are not shown and the
  tab says so.
- Markdown parsing, YAML frontmatter, Mermaid diagram rendering, and document link
  normalization are built in.
- Above the viewer, the SDD execution panel checks readiness for a spec and pull
  request and starts a native run. Selecting a document under
  `specs/<YYYY-MM>/<bundle>/` fills in that spec.
- Data comes directly from the autohub repository API
  (`/api/v1/projects/{project_id}/repository/*`).
