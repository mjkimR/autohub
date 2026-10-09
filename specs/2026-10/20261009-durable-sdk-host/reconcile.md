# Living documentation reconciliation

Status: resolved. The SDK README and root README now distinguish SDK contracts
from the implemented backend host. `docs/sdk-task-flow.md` describes scoped machine
ownership, immutable snapshots, approval/deadline/rework/resume and cancel recovery.
`docs/development.md` documents server target configuration, worker idempotency and
cancellation tombstones, dispatch timing and isolated PostgreSQL test configuration.
`docs/delivery-status.md` records local implementation without implying deployment.

Workbench architecture and task-flow design record F2 implementation and keep F3
(planhub application plus specrig/PR adapter) and F4 (scope/coordination) separate.
No workflow stage is copied from specrig and existing PR runs remain independently
owned. Generic scoped machine approval does not claim PR approval evidence.

Boundary additions: `.dockerignore` preserves SDK README wheel metadata; the
existing project observation test adopts its sibling tests' SQLite-only dispatcher
isolation fixture, preventing concurrent StaticPool transactions from interfering.
PostgreSQL still exercises concurrent workers, requests and approval commands.

Remaining limits: no automatic SDK-flow retention, worker code deployment, PR
adapter, planhub application integration or operating deployment. A five-minute
production dispatcher tick bounds latency despite five-second polling eligibility.
No files were staged and no commit, PR, release or deployment was created.
