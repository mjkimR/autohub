# devkit integration

This is the current integration and runtime contract. For dated local verification
and deployment evidence, see [delivery status](delivery-status.md). A capability
being implemented here does not establish that the serving production revision has it.

## Responsibilities

| Owner | Responsibility |
| --- | --- |
| Repository documents | Milestones, proposal decisions, specs and workflow evidence |
| devkit / devkit-spec | Workflow definitions, next-stage evaluation, rules, envelope and decision formats |
| Auto Hub | Cloud activity start, agent delivery, quotas, durable runs, operator actions, CI observation and merge control |
| devkit-viewer | Read-only document and roadmap rendering; Hub supplies authenticated repository data and execution links |

Hub consumes the pinned CLI's structured results. It keeps its own execution lease,
head/base checks and approval evidence; repository decisions alone do not authorize
Hub to merge. Tick, webhook and manual advancement use the same bounded progression
function, continuing until external work, a gate or another real wait is reached.
See [execution timing](development.md#pipeline-advancement) for the detailed limits.
Approval report cards use `devkit workflow envelope check --details --format json`:
the default inspection omits report summaries and checks.
Planning cards preserve worker effort, support-role rounds and reverify links;
their review gaps are guidance, while the CLI remains the source of gate state.

## Supported paths

| Starting point | Action |
| --- | --- |
| Draft proposal with recorded or delegated plan-intent, no decomposition needed | Start Planning on `plan-<slug>`, review, accept or reject |
| Accepted proposal | Start Development on `dev-<slug>`, hand off to a spec, continue its workflow |
| Existing PR and bound spec/proposal | Check readiness and enroll the same PR |
| Externally implemented, paused PR | SDK bridge verifies evidence and requires scoped approval before resuming its owner |

Planning and Development start/decision rules are in
[run decisions](run-decisions.md#starting-planning-and-development). Existing-PR
execution is available in the [SDD repository panel](repository-viewer.md); the
[SDK bridge](development.md#sdk-flow-bridge-with-an-existing-pr) has a separate
server allowlist and checkout requirement. Work Plans do not create native SDD specs.

The roadmap reads milestone definitions and direct proposal members from the
selected branch. Spec metadata does not establish milestone membership. Selecting
a member fills the execution unit and shows Run/Decisions and GitHub PR links.
Select a `plan-*` or `dev-*` branch first to inspect its documents; the viewer
does not aggregate remote branches. Reading a milestone or member does not start work.
Related executions include the proposal and spec connected by a recorded
`handoff_from` in the same project. Matching slugs alone do not establish lineage.
See [viewer behavior and limits](repository-viewer.md).

## Runtime profiles

[The default manifest](../config/sdd-runtime/pyproject.toml) and its
[lock](../config/sdd-runtime/uv.lock) pin the Python runtime separately from Hub's
dependencies. The lock includes dependency hashes and one immutable devkit monorepo
commit for `devkit-agt`, `devkit-advisory` and `devkit-spec` (the latter from
`packages/devkit-spec`), plus their `devkit-dist`, `devkit-core`, `devkit-cli` and
`devkit-docs` dependencies. The manifests' `[tool.uv.sources]` are the only record of
that commit and of the `app-tools` commit; `uv.lock` records the resolved versions.
Update the sources together and regenerate the lock. The app-common profile and Hub's
development environment use the same `app-tools` commit as
[Hub's manifest](../modules/hub/pyproject.toml); their UV overrides keep its
transitive devkit pins on the reviewed devkit commit.
The isolated CLI entrypoint is `python -I -B -m devkit_dist`.
Hub hashes the effective workflow JSON itself: current devkit bindings identify a
workflow by name, while Hub still refuses definition or policy changes during a run.

### Install and verify

For a fresh local setup, provision both reviewed profiles, then run the CLI contract tests:

```sh
just install-sdd
just install-sdd .cache/sdd-app-common config/sdd-runtime-app-common
export AUTOHUB_SDD_HOME="$(pwd)/.cache/sdd"
just test-sdd
```

Git credentials or build-only `GH_TOKEN` must permit access to the pinned devkit repository
and, for the app-common profile, app-common. The installer stores no token in its
manifest or pin. The runtime defaults to
`/opt/sdd`; its `pin.json` records the lock digest, the package versions and the
Git revisions the lock resolves (a runtime provisioned before revisions were
recorded only loses the parity warning below). Hub snapshots the lock digest, provider, workflow
hash, policy and configuration/receipt digest. Updates require a reviewed lock and
a new run.

The default profile contains the spec, devkit and advisory bundles. The additional
[app-common manifest](../config/sdd-runtime-app-common/pyproject.toml) and
[lock](../config/sdd-runtime-app-common/uv.lock) add the reviewed `app-tools` package
(the app-common bundle); its override pins the transitive devkit toolchain to the
same monorepo commit. The installer records the available bundle names in `pin.json`.
Readiness checks both selected bundles and the committed receipt against that inventory,
then lets devkit validate presets and restore assets. Missing bundles refuse execution
with `SDD_BUNDLES_MISSING`, naming the selected profile and missing bundle identifiers.
No project dependency is installed during a request.

### Assign repositories

The standard image already contains these two runtime directories. When provisioning
a host yourself, install them before assigning repositories in server-owned configuration:

```sh
just install-sdd /opt/sdd
just install-sdd /opt/sdd-app-common config/sdd-runtime-app-common
export AUTOHUB_SDD_PROFILES='{"profiles":{"app-common":"/opt/sdd-app-common"},"repositories":{"owner/repository":"app-common"}}'
```

Unmapped repositories use `AUTOHUB_SDD_HOME` (default `/opt/sdd`). Profile paths must
be absolute; invalid mappings fail closed. Repository names are matched without case.
The same repository mapping applies to inspection, decisions, activity creation and
the SDK bridge. Selection is scoped to each asynchronous operation, so concurrent
projects cannot inherit each other's runtime. `/sdd/runtime` reports the project's
profile, bundle inventory and isolation probe; the UI shows them under **Check runtime**.
The immutable lock remains part of each execution snapshot and bridge approval digest:
changing a profile's lock requires a newly enrolled run, not an in-place upgrade.
The installer refuses to replace a destination whose lock differs; use a new
directory when updating locally. Settle existing runs before changing their runtime.

When adopting another devkit commit, preserve the existing installation directories and
provision fresh profiles (any new directory names) before switching the host configuration:

```sh
just install-sdd .cache/sdd-next
just install-sdd .cache/sdd-app-common-next config/sdd-runtime-app-common
AUTOHUB_TEST_SDD_APP_COMMON="$PWD/.cache/sdd-app-common-next" just test-sdd .cache/sdd-next
```

After settling active runs, set `AUTOHUB_SDD_HOME` and any `AUTOHUB_SDD_PROFILES`
mapping to these absolute paths (or deploy the image's refreshed `/opt/sdd` and
`/opt/sdd-app-common`). Sync and commit consumer receipts with matching packages
before enrolling replacement runs. The installer records versions and revisions
for all six devkit distributions, including the new CLI owner.

### Add or update a profile

For another bundle set, commit a reviewed manifest and lock in a separate config
directory and pass that directory as the second `just install-sdd` argument. Never
use a target PR's manifest. Package that directory into the deployment image explicitly.
The standard image contains both `/opt/sdd` and `/opt/sdd-app-common`; setting the
repository mapping chooses the latter. The contract suite needs both profiles;
`AUTOHUB_TEST_SDD_APP_COMMON` overrides its default `.cache/sdd-app-common` test path.

## Repository contract and evidence

Each evaluation fetches exact PR head/base commits into a disposable checkout.
The project must commit `.devkit/config.toml` and `.devkit/installation.json`;
managed copies and projections stay ignored. `devkit sync --locked` restores
missing generated assets using installed packages, without changing the receipt,
guidance or seed documents. When the committed receipt no longer matches the
runtime's packages (`RECEIPT_STALE`), Hub regenerates the assets with a plain
`devkit sync` in the same disposable checkout and continues: the snapshot still
digests the committed receipt, and a `RECEIPT_STALE` warning appears in a
successful readiness result, in the run evidence and in the agent instructions;
when a later step refuses after such a restore, its reason names the stale receipt.
A plain sync that itself fails (`SYNC_CONFLICT`, `OVERRIDE_DRIFT`,
`SELECTION_INVALID`) still blocks. Proposal decisions are the one write path: Hub
commits inside the sandbox as `AUTOHUB_SDD_COMMIT_IDENTITY` (`Name <email>`, default
`AutoHub <autohub@users.noreply.github.com>`) and pushes outside it with the connector
token under a lease on the confirmed head ([run decisions](run-decisions.md#proposal-decisions)).
The final `lint-ci-clean` check reads the
committed tree and enforces exactly the rule set the committed receipt records, so
a stale receipt integrates under that older rule set; a recorded rule whose
regenerated copy no longer loads pauses the run with the lint diagnostic instead of
dispatching repair work, because no agent attempt can fix it within the run. Commit
the receipt the reviewed runtime produces, then enroll the pull request again: a
receipt commit changes the configuration digest, as any devkit configuration
change does, and agents are told not to change `.devkit/` mid-run for that reason.
No initialization or upgrade fallback runs, and no repository dependency is ever
installed. Agents work from
the repository's own devkit installation, which Hub cannot inspect: when the
repository's root `uv.lock` pins `devkit-spec` or `devkit-agt` at another revision
than the runtime, a `RUNTIME_REVISION_MISMATCH` warning is the only parity signal.
A repository that ignores the entire `.devkit/` directory must explicitly adopt
this consumer contract before it can be enrolled; Hub does not change its policy.

## Isolation and deployment

Python rules and workflow-check packages are executable code. All devkit commands
run through OS isolation, with a writable disposable checkout, read-only runtime
and system tools, no server credentials and no network. Linux needs bubblewrap
and permission to create unprivileged namespaces; macOS uses sandbox-exec. There
is no unsandboxed fallback. Validate namespace support on the actual container
host: installing bubblewrap alone does not establish support, including on
managed Cloud Run deployments (bubblewrap needs unprivileged user namespaces, which
the first-generation execution environment does not provide; deploy with
`--execution-environment=gen2`). `GET /api/v1/projects/{id}/sdd/runtime` (the
**Check runtime** button of the repository's SDD panel) starts devkit inside the
sandbox on the serving host and reports the runtime pin, so a new host is checked
without a pull request. Unsupported hosts fail readiness and need a compatible
execution host before native SDD can run.

Only completed checks with rule violations become repair work; setup, loading
and execution failures block, except that a recorded rule which no longer loads
under a stale receipt pauses the run as described above.
The JSON `error`/`errors` contract and exit
status drive this distinction. Repository stderr and free-form error messages
are never returned to users. The old Go runner/cache and release installer are removed.

The Dockerfile packages the locked environment as read-only runtime files and
installs Git and bubblewrap. Local builds pass `GH_TOKEN` using a BuildKit secret;
Cloud Build uses `SDD_BUILD_SECRET=<Secret Manager secret name>` in the same GCP
project. Grant its build identity secret access. The final image contains private
devkit assets, so distribute it according to the source repositories' access policies.

### Migrating legacy runs

When upgrading from the legacy specrig implementation, apply migration
`ba3d1a6089a9` with the matching backend and frontend. It renames
project mode and run columns, preserves snapshot/decision history verbatim, and
cancels nonterminal legacy runs and their open attempts. It does not stop agent
work already posted to GitHub: settle it before enrolling replacement work.
Legacy snapshots are read-only; they cannot be resumed with the new provider.
The downgrade also settles active SDD work before exposing it to the old backend.

## Live canary after deployment

Use a designated test repository and PR with the matching runtime receipt and
bound workflow. This is an external-write test and must use an approved target.

1. Check readiness, start the native run, and follow its link from the spec view.
2. Reach a draft human gate; verify the wait releases its execution slot and the
   Decisions dialog links report evidence to the actual inspected commit.
3. Exercise a provider question, save an answer, then explicitly resume with it.
   Verify the next request contains that selected answer without implied approval.
4. Approve integration, revoke before progression, and confirm no merge. Request
   changes and verify a changed head requires renewed evidence/approval.
5. Explicitly approve the final evidence, mark the test PR ready, then confirm the
   configured CI checks and merge policy complete that same PR exactly once.
6. Keep run/PR links and the approval history as canary evidence. Local mock tests
   do not establish provider question behavior, GitHub protection or live delivery.


## Deferred: multiple proposals and milestone execution

As of 2026-10-19, automatic Work Plan ↔ devkit unit linkage and milestone-wide
execution are deferred. Use the roadmap to inspect work and the existing individual
Planning/Development actions to start it. Milestone membership does not imply an
execution order, admission or approval, and `group_key` is not a milestone binding.

Revisit this when repeated multi-proposal execution needs a shared dependency or
failure policy. A candidate flow is **select targets from a milestone → review a
fixed execution list → start the batch**, with every proposal retaining its existing
gates. This is a design direction, not an implemented API or an approved final contract.
Before implementation, decide:

- Whether drafts enter Planning or only accepted proposals enter Development.
- Where execution dependencies and ordering are recorded.
- Whether new milestone members join an already started batch.
- Whether a failed member stops independent remaining work, and how retries are owned.

Repository documents continue to own direction and specs. Any future Work Plan
adapter should reference unit paths and milestone IDs; duplicating those documents
or treating milestone completion as blanket merge approval is outside the current contract.
