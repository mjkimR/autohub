# Repository Viewer and SDD Projects

Set `project_type` according to the kind of project (`general` / `sdd`).
The built-in repository viewer adapts its screen to the project type.

## Project modes

| Mode (`project_type`) | Description |
| --- | --- |
| `general` | Default Git browser (directory tree, file contents, README preview) |
| `sdd` | Spec-driven project viewer for `devkit-spec` repositories (release handbook and Living Spec reading, Proposals and Specs indexes, milestone roadmap, file explorer), the native SDD run panel, and the Git browser |

Choose `Project Type` in the project settings or when registering a new project.
See [devkit runtime profiles](devkit-integration.md#runtime-profiles) for the runtime the
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
- **Sdd View** includes a dashboard and a Read tab (the release handbook when
  `handbook/manifest.json` exists, with Living Spec indexing on request),
  `Proposals` (`docs/proposals/PROP-*/` bundles), `Specs` (`specs/` task bundles)
  (the Proposals panel above the viewer starts and decides proposals; see
  [run decisions](run-decisions.md#proposals-panel)),
  `Roadmap` (`docs/roadmap/MS-*.md` milestones by status, `depends_on` readiness and
  direct member proposals) and `Files` (file explorer), with search and status
  filters. With the viewer from devkit 0.1.4, milestones and their members come from
  the selected branch. Only `docs/proposals/PROP-*/proposal.md` anchors establish
  membership; historical `milestone` fields on specs are ignored. Select a `plan-`
  or `dev-` branch in the repository selector to inspect its saved documents.
  The viewer no longer aggregates remote activity branches into the roadmap.
- A member opens its source document on the selected branch. Selecting a spec or
  proposal fills the execution unit and shows its recent
  Run/Decisions links and direct GitHub PR links. A recorded `handoff_from` joins
  related proposal and spec executions within the same project; similar names
  alone do not join them. Reading never starts a run or grants approval.
- Markdown parsing, YAML frontmatter, Mermaid diagram rendering, and document link
  normalization are built in.
- Above the viewer, the SDD execution panel checks readiness for a unit and pull
  request and starts a native run. It accepts specs and proposals; the Proposals
  panel provides the separate Planning/Development start and decision actions.
- Data comes directly from the autohub repository API
  (`/api/v1/projects/{project_id}/repository/*`).

## Execution scope

The roadmap is read-only. Starting all members of a milestone, linking them to a
Work Plan, and multi-proposal dependency/failure policies are
[deferred](devkit-integration.md#deferred-multiple-proposals-and-milestone-execution).
Use individual proposal actions and unit execution links with the existing gates.
