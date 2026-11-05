# Operate the isolated SDD runtime

Provision the reviewed runtime before enrolling native SDD work. Its product
contract is `CAP-SDD-runtime-isolation`; `CAP-SDD-workflow-control` owns workflow
and integration decisions. Deployment structure belongs to `ARCH-07-deployment`.
Contributor test selection and pin changes belong in the
[development testing guide](../development/testing.md).

## Runtime profiles

The standard image contains `/opt/sdd` and `/opt/sdd-app-common`. The latter adds
the app-common bundle. From a trusted Auto Hub checkout, a separately provisioned
host can install the same reviewed profiles:

```sh
just install-sdd /opt/sdd
just install-sdd /opt/sdd-app-common config/sdd-runtime-app-common
```

Use only operator-reviewed manifests/locks under `config/sdd-runtime*`; never use
a target PR's manifest. Provisioning needs read access to the pinned private
sources. The installer can consume `GH_TOKEN` during provisioning without storing
it in manifest URLs or `pin.json`. It records runtime lock digest, package
versions, Python prefix, bundle inventory and exact available Git revisions.

The installer refuses to replace a destination whose recorded lock differs.
Provision a fresh destination for an update. A runtime directory and its lock/pin
must stay available and consistent for the runs admitted against that identity.
No request installs a target repository's dependencies.

## Assign repositories

Configure mappings on the server after provisioning their absolute paths:

```sh
export AUTOHUB_SDD_HOME=/opt/sdd
export AUTOHUB_SDD_PROFILES='{"profiles":{"app-common":"/opt/sdd-app-common"},"repositories":{"owner/repository":"app-common"}}'
```

Unmapped repositories use the default runtime. Repository names match without
case; invalid or unknown mappings fail rather than silently using another profile.
The same mapping applies to activity creation, readiness, decisions and SDK evidence.

For another bundle set, add a reviewed manifest/lock under a distinct config
directory, pass that directory as the second `just install-sdd` argument and package
its runtime directory in the deployment image. Confirm its `pin.json` inventory
contains the repository's selected and receipt-recorded bundles.

When changing runtime identity:

1. Identify active runs using the affected profile and settle their external work.
2. Provision the reviewed replacement in a fresh directory or deployment image;
   retain existing runtime directories while their admitted runs need them.
3. Switch the serving configuration to the replacement's absolute paths.
4. Check the selected profile on the serving host through **Check runtime** or
   `GET /api/v1/projects/{project_id}/sdd/runtime`.
5. Align each consumer's committed config/receipt with the reviewed packages before
   enrolling replacement runs. A changed receipt/configuration requires new enrollment.

Do not treat a profile switch as an in-place workflow upgrade for an existing run.
The lock/runtime/workflow/configuration identity remains part of its admitted
contract and any bridge evidence digest.

## Consumer configuration and recovery

The connected repository needs committed regular `.devkit/config.toml` and
`.devkit/installation.json` files and its bound proposal/spec anchor. Keep managed
copies and agent projections ignored. Readiness is an inspection, not execution
or merge authorization.

| Reported condition | Operator action |
| --- | --- |
| `SDD_RUNTIME_UNAVAILABLE` | Provision/check the selected runtime and its matching lock/pin |
| `SDD_PROFILE_INVALID` | Correct server-owned profile paths and repository mappings |
| `SDD_ISOLATION_UNAVAILABLE` | Provision/enable a supported isolation runner on a compatible host and repeat its runtime probe |
| `SDD_BUNDLES_MISSING` | Provision the missing bundle set and assign that reviewed profile |
| `SDD_RECEIPT_MISSING` | Have the repository adopt and commit its consumer configuration/receipt before enrollment |
| `RECEIPT_STALE` warning | Align and commit the consumer receipt with reviewed packages, then enroll again; disposable restoration does not update its committed identity |
| `RUNTIME_REVISION_MISMATCH` warning | Compare the consumer's locked Git revisions with the runtime pin; the warning cannot inspect the agent's installed environment |
| Final lint cannot load a stale receipt's recorded rule | Fix the consumer/runtime receipt alignment and enroll again; generic resume cannot dispatch an agent to repair that setup failure |
| Workflow, policy or runtime identity changed | Review the new contract and create a new enrollment rather than renewing the old run implicitly |

A stale-receipt warning permits only the documented disposable restore exception.
Other sync failures still stop evaluation. Do not ask the active worker to change
`.devkit/` to clear the warning mid-run.

## Isolation and deployment

Linux evaluation uses bubblewrap; macOS uses sandbox-exec. The host must permit the
required isolation, including unprivileged namespaces for bubblewrap. Installing
the binary or successfully building an image does not prove that the serving host
can execute it. There is no unsandboxed fallback.

The runtime probe starts devkit inside isolation without a PR. Require `ok: true`
for the intended profile on the actual serving host before native SDD rollout.
Unsupported isolation needs a compatible execution host. For Cloud Run, configure
an execution environment with the required namespace support; the deployment helper
does not select that environment automatically. If selecting the second-generation
environment, configure `--execution-environment=gen2` and still verify the probe.

The image packages Git, bubblewrap and the locked runtime files. Local builds can
supply the private-source credential through the BuildKit `sdd_token` secret.
The Cloud Build helper accepts `SDD_BUILD_SECRET=<Secret Manager secret name>` in
the same GCP project; its build identity needs secret access. The final image
contains private devkit assets and follows their source access policy.
See the [deployment procedure](cloud-run-deployment.md) for serving configuration.

The bridge additionally needs a separately provisioned clean checkout. Its
allowlisted target and managed-machine setup belong in the
[SDK worker operations guide](execution-targets.md); runtime provisioning does not create
that checkout or deploy worker code.

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

Use a designated test repository and PR with the matching committed runtime
receipt and bound workflow. Run this external-write test only against its approved
target; local CLI/mock tests do not establish provider or GitHub behavior.

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
