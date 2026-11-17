# Impeccable context

This folder is the tracked source of the project context that the Impeccable design
plugin reads. Edit the files here, not at the repository root.

Impeccable reads `PRODUCT.md`, `DESIGN.md` and an optional `.impeccable/` directory
from the repository root. The root `PRODUCT.md` is a relative symlink to
[PRODUCT.md](PRODUCT.md) in this folder. The link itself is kept out of Git by the
`/PRODUCT.md` entry in `.git/info/exclude`, so each checkout or linked worktree needs
its own link. Create or verify it from the repository root with the
`app-uiux-improve` bundle's link script, which defaults to this folder and also
checks the expected `.git/info/exclude` entries:

```sh
sh .devkit/managed/app-uiux-improve/skills/app-uiux-improve/scripts/link-impeccable-context.sh
sh .devkit/managed/app-uiux-improve/skills/app-uiux-improve/scripts/link-impeccable-context.sh --check
```

`DESIGN.md` is intentionally absent. The design authority is the
[visual style](../../steering/visual-style.md) steering document; do not create a
separate `DESIGN.md` that could diverge from it.
