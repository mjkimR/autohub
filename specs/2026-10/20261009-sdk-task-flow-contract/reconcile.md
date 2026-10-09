# Living documentation reconciliation

The SDK README describes version-1 compatibility and version-2 remote contracts.
`docs/sdk-task-flow.md` records the available SDK behavior and the absent backend
host APIs. `docs/delivery-status.md` and the root README distinguish local client
validation from deployed execution. The new code does not import backend modules.

The consumer's installed wheel and HTTP/CLI tests verify the protocol across the
repository boundary. Future durable-host work remains in workbench F2–F4 and
planhub PROP-autohub-delivery-host; production SDK pins require publication or a
pushed commit. Documentation extends the task boundaries to describe the new
contract. Existing backend architecture warnings were unchanged. No index,
commit, release, PR, merge, or deployment was created.
