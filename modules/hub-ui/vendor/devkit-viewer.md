# Pinned repository viewer artifact

`devkit-viewer-0.1.0.tgz` is the SDD repository viewer library (`SddViewer` and its roadmap view), built without
source edits from `mjkimR/devkit` commit `fa6aa90f783b63c0708e320a25a245c822836133`, directory
`packages/devkit-viewer/frontend`. devkit owns its source; npm Git dependencies install only a repository's root
package, so this nested package is distributed as a committed artifact. `package-lock.json` pins the artifact's
npm integrity. The repository view passes its own `repositoryDataSource`; the library adds no autohub API call.

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

Never use a sibling checkout path as a dependency or edit an installed package.
