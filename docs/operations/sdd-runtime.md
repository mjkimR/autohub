# Operate the isolated SDD runtime

Native SDD evaluation runs devkit from the runtime that each evaluated commit's
own `uv.lock` pins; Hub installs it on first use into a per-instance cache. Its
product contract is `CAP-SDD-runtime-isolation`; `CAP-SDD-workflow-control` owns
workflow and integration decisions. Deployment structure belongs to
`ARCH-07-deployment`. Contributor test setup belongs in the
[development testing guide](../development/testing.md).

No server runtime profile exists. Onboarding a devkit-adopted repository needs no
image change, profile mapping or redeploy. Hub reads neither `AUTOHUB_SDD_HOME`
nor `AUTOHUB_SDD_PROFILES`; remove them from serving configuration.

## Consumer requirements

A connected repository is evaluable when its evaluated commit has:

- A committed root `pyproject.toml` that declares `devkit-spec` in a dependency
  group (Hub uses the first such group) or in its main dependencies, and a
  committed root `uv.lock` that is current for it. Only that group is installed.
- A `requires-python` range that includes the image interpreter (Python 3.13).
- Locked packages of that group from PyPI as hashed wheels, or Git sources on
  `https://github.com/` pinned to exact revisions. Path, URL, editable and
  custom-index sources are refused, as are registry packages without wheels.
- Git sources that the project's GitHub connector token can read and that build
  with hatchling, the backend the image pins.
- Packages providing every bundle its `.devkit/config.toml` presets and
  `.devkit/installation.json` receipt name.
- Committed regular `.devkit/config.toml` and `.devkit/installation.json` files and
  its bound proposal/spec anchor. Keep managed copies and agent projections ignored.

Readiness is an inspection, not execution or merge authorization.

## Serving host

Serve native SDD from Linux with bubblewrap. The host must permit unprivileged
user namespaces. macOS sandbox-exec cannot end detached processes a sandboxed step
leaves, so use it for local development only. There is no unsandboxed fallback.

The standard image packages Git, bubblewrap, `uv` and the pinned build environment
`/opt/sdd-build`; it contains no devkit runtime. The Hub process needs outbound
access to `https://github.com/` and PyPI for installs.

| Variable | Default | Set it when |
| --- | --- | --- |
| `AUTOHUB_SDD_CACHE` | `/tmp/autohub-sdd-runtimes` | The cache needs another writable directory |
| `AUTOHUB_SDD_CACHE_BYTES` | `268435456` (256 MiB) | Instance memory or the number of distinct locks differs from the default sizing |
| `AUTOHUB_SDD_BUILD` | `/opt/sdd-build` | A host is not using the standard image layout |

The default cap holds about eight 29 MiB entries and leaves room on a 1 GiB
instance for one install's 153 MiB transient peak (measured for
`SPEC-repo-locked-sdd-runtime`). On Cloud Run, `/tmp` is in-memory: the cache
counts against instance memory and is empty after each instance start. Entries
are shared by every project of the instance that locks the same runtime.

## Check a host and a project

Use **Check runtime** in the SDD panel or:

```sh
curl -s "$SERVICE_URL/api/v1/projects/<project-id>/sdd/runtime"
```

1. Require `ok: true` with `isolation: bubblewrap` on the actual serving host. The
   host probe starts the image interpreter inside the sandbox and installs nothing;
   a passing image build does not prove the serving host can run the sandbox.
2. Read `state` for the project's default-branch head: `ready` lists `bundles` and
   `revisions`; `preparing` means an install is running, so check again shortly;
   `failed` carries `lock_detail` with the remediation. Checking the state can
   start that install.

## Troubleshooting

Readiness reports these codes as `ready: false` with a diagnostic; enrollment
returns them as HTTP errors; a running native run blocks with them.

| Reported condition | Operator action |
| --- | --- |
| `SDD_RUNTIME_PREPARING` (HTTP 503) | Wait for the install and retry; a running native run keeps its state and is inspected again on later dispatcher ticks, and blocks after 45 minutes of preparing until it is resumed |
| `SDD_RUNTIME_UNLOCKED` | Commit a root `uv.lock` current with a `pyproject.toml` that declares `devkit-spec` |
| `SDD_RUNTIME_SOURCE_UNSUPPORTED` | Lock devkit packages only from PyPI wheels or exact `https://github.com/` revisions |
| `SDD_RUNTIME_PYTHON_UNSUPPORTED` | Widen `requires-python` to include Python 3.13 |
| `SDD_RUNTIME_SOURCE_UNAVAILABLE` | Grant the project's GitHub connector read access to each locked Git source; a request after the 10-minute failure marker expires starts a new install |
| `SDD_RUNTIME_INSTALL_FAILED` | Check that registry packages provide wheels and Git sources build with hatchling; a request after the 10-minute failure marker expires starts a new install |
| `SDD_RUNTIME_UNAVAILABLE` | Check that the host's `uv` binary runs and the cache directory is writable, then retry |
| `SDD_ISOLATION_UNAVAILABLE` | Run on a Linux host with bubblewrap and user namespaces and repeat the host probe |
| `SDD_BUNDLES_MISSING` | Add the packages providing the named bundles to the locked devkit group and commit `uv.lock` |
| `SDD_RECEIPT_MISSING` | Have the repository adopt and commit its consumer configuration/receipt before enrollment |
| `RECEIPT_STALE` warning | Run `devkit sync` with the locked `devkit-spec`, commit the receipt, then enroll again; disposable restoration does not update its committed identity |
| Final lint cannot load a stale receipt's recorded rule | Align the committed receipt with the locked runtime and enroll again; generic resume cannot dispatch an agent to repair that setup failure |
| Workflow, policy or configuration identity changed | Review the new contract and create a new enrollment rather than renewing the old run implicitly |

Install failures stay visible for 10 minutes. Keep the external dispatcher and maintenance trigger at an interval
shorter than that so SDK bridge checks report the failure instead of retrying `bridge-unavailable`; native runs
block after 45 minutes of preparing whatever the interval.

A changed runtime identity alone continues a run and records the new
`devkit-lock:<identity>`. `SDD_PROFILE_INVALID` and `RUNTIME_REVISION_MISMATCH`
appear only on records retained from the server-profile model. A stale-receipt
warning permits only the documented disposable restore exception. Other sync
failures still stop evaluation. Do not ask the active worker to change `.devkit/`
to clear the warning mid-run.

## Rollout and rollback

Records admitted under server profiles carry `devkit-spec:<lock>` CLI identities
and the old batch `runtime` shape; batch comparisons treat that shape as a change.
Before deploying the repository-locked runtime, and again before rolling back to an
image with server profiles:

1. Settle active native runs: let them finish, or cancel them and inspect provider
   work already posted to GitHub.
2. Settle open batch selections.
3. Settle approved bridge claims that have not resumed their PR.
4. Deploy, then check the host probe and each project's lock state as above.
5. Enroll replacement runs and batches against the new image.

Hub enforces none of these steps.

## Isolation and deployment

For Cloud Run, configure `--execution-environment=gen2` for the namespace support
bubblewrap needs; the deployment helper does not select it automatically. Verify
the host probe after every deploy. The image build needs no source credential. See
the [deployment procedure](cloud-run-deployment.md) for serving configuration.

A cold install runs as a background task in one worker process and measured 11-18
seconds in a local container shaped like the service (cpu=1, 1 GiB). With
request-based CPU allocation, Cloud Run throttles CPU between requests, which can
lengthen it; this has not been measured on the serving host.

The bridge additionally needs a separately provisioned clean checkout whose own
root `uv.lock` declares devkit. Its allowlisted target and managed-machine setup
belong in the [SDK worker operations guide](execution-targets.md).

## Migrating legacy runs

An installation upgrading from the legacy provider must apply migration
`ba3d1a6089a9` with matching backend/UI. It renames the stored project mode and
run columns, preserves snapshots/decision history and cancels nonterminal legacy
runs and their open attempts. The downgrade also settles active work before
exposing records to the old backend.

Inspect and settle provider work already posted to GitHub before enrolling
replacement runs: the database migration cannot stop it. Legacy snapshots remain
read-only and cannot resume against devkit-spec. The migration and its limits are
anchored by the [migration regression](../../modules/hub/tests/integration/features/project_management/sdd/test_migration.py).

## Live canary after deployment

Use a designated test repository and PR with a committed devkit lock, matching
committed receipt and bound workflow. Run this external-write test only against
its approved target; local CLI/mock tests do not establish provider or GitHub
behavior.

1. Check the runtime state until it is `ready`, check readiness, start the native
   run, and follow its link from the spec view.
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
