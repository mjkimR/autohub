# Pinned repository viewer artifact

`devkit-viewer-0.1.0.tgz` is the SDD repository viewer library (`SddViewer` and its roadmap view), built without
source edits from `mjkimR/devkit` directory `packages/devkit-viewer/frontend` at the devkit commit pinned in the
root [`pyproject.toml`](../../../pyproject.toml) `[tool.uv.sources]`. Rebuild it whenever that pin changes. devkit owns its source; npm Git dependencies install only a repository's root
package, so this nested package is distributed as a committed artifact. `package-lock.json` pins the artifact's
npm integrity. The repository view passes its own `repositoryDataSource`; the library adds no autohub API call.
The frontend library retains its independent npm version `0.1.0`; the root devkit pin identifies its source.
This artifact was built from devkit 0.1.6, commit `b151a10bb4ab9433c1dbaeb6c316917c959b6ba0`.
The machine-readable [source receipt](devkit-viewer.source.json) records the reviewed source commit, devkit release
version and artifact SHA-256. `just check-devkit` compares it with all three Python environments and the tarball's
npm integrity; the viewer's npm version remains independent of the devkit release version.
Roadmap membership follows direct proposal anchors; global and package namespace milestones, including archives,
are discovered on the selected branch. The Read tab supports the release handbook.
Local-only Planning overlays and shared artifacts are optional data-source capabilities and are not enabled here.

To rebuild, use a clean checkout of that published commit (Node and npm):

```sh
just viewer install
just viewer pack /absolute/path/to/this/frontend/vendor
```

`just viewer pack` checks that the tarball holds the library only and exports `SddViewer`, `httpDataSource` and
`RepositoryDataSource`. Then reinstall the artifact explicitly to refresh the lockfile and its integrity, even when
the package version has not changed:

```sh
npm install ./vendor/devkit-viewer-0.1.0.tgz
```

Update `vendor/devkit-viewer.source.json` after rebuilding. Take `commit` from `git rev-parse HEAD` and `version`
from `VERSION` in the clean devkit checkout used for the build. Record the rebuilt tarball's SHA-256, obtained
with `shasum -a 256 vendor/devkit-viewer-0.1.0.tgz` from this frontend directory. Keep `schema`, `repository` and
`artifact` unchanged unless their contract changes. From the autohub root, run `just check-devkit` and commit the
tarball, source receipt and npm lockfile together.

Never use a sibling checkout path as a dependency or edit an installed package.
