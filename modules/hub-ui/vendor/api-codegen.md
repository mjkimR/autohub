# Pinned API generator artifact

`app-common-api-codegen-0.1.0.tgz` is built without source edits from
`mjkimR/app-common` commit `38711a6f2a3902416280450eb7f864360044366b`, directory
`packages/ui/app-ui-api-codegen`. npm Git dependencies install the root ESLint
package, so this nested package is distributed as a committed artifact.
`package-lock.json` pins the artifact's npm integrity.

To rebuild, use a clean checkout of that published commit:

```sh
npm ci --prefix packages/ui/app-ui-api-codegen
npm pack ./packages/ui/app-ui-api-codegen --pack-destination /absolute/path/to/this/frontend/vendor
```

Then reinstall the artifact explicitly to refresh the lockfile and its integrity,
even when the package version has not changed:

```sh
npm install --save-dev ./vendor/app-common-api-codegen-0.1.0.tgz
```

Never use a sibling checkout path as a dependency or edit an installed package.
