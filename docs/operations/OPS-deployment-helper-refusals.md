---
id: OPS-deployment-helper-refusals
title: "Cloud Run deployment and scheduler provisioning refusal routing"
status: active
summary: "Routes a stopped Cloud Run deployment helper, secret bundle setup or Cloud Scheduler provisioning run to existing owners by its printed refusal and the Secret Manager and machine-key state; trigger staleness and missed webhooks after a completed deployment are out of scope."
related_capabilities:
  - CAP-ACCESS-authentication-authorization
  - CAP-EXEC-scheduling-maintenance
---

# [OPS-deployment-helper-refusals] Cloud Run deployment and scheduler provisioning refusal routing

`just setup-secrets`, `just deploy-cloud-run` or `just provision-scheduler` stops before the external tick is
configured. The scheduler provisioning helper prints only sanitized messages and never echoes `gcloud` output,
because that output can carry a credential header. A failure message therefore names the refused state, not its
cause. The cause comes from comparing the message with the `autohub-secrets` bundle, the
`<service>-scheduler-credential` secret and the `<service>-scheduler` machine's keys.

## Routing

`just provision-scheduler` reads `APP_API_KEY_ROOT_KEY` from the latest `autohub-secrets` version and calls the
machine management API on the deployed service with `X-Root-API-Key`. `just deploy-cloud-run` runs the same
helper after `gcloud run deploy` unless `--no-scheduler` is passed.

| Symptom or state | Discriminating evidence | Next useful owner |
| --- | --- | --- |
| Secret setup refuses an existing bundle | `just setup-secrets` prints `Error: 'autohub-secrets' exists but its latest version cannot be read.`; the bundle exists, but the caller cannot access its latest version | [Secret Manager configuration](../runbooks/cloud-run-deployment.md#3-secret-manager-configuration) and [IAM permissions](../runbooks/cloud-run-deployment.md#4-service-account-iam-permissions) |
| Secret setup refuses missing input | `just setup-secrets` prints `--email is required the first time` or `--database-url or --connection-name is required`; no bundle value supplies it | [Secret Manager configuration](../runbooks/cloud-run-deployment.md#3-secret-manager-configuration) |
| New revision never serves | `gcloud run deploy` reports a revision that is not ready, and the container log shows an `alembic upgrade head` failure before Uvicorn starts | `ARCH-07-deployment` Deployment artifact; [schema update](../runbooks/sdd-runtime.md#schema-update) |
| Provisioning lacks the root credential | `The secret bundle needs APP_API_KEY_ROOT_KEY; run just setup-secrets and redeploy` | [Cloud Scheduler registration](../runbooks/cloud-run-deployment.md#6-register-cloud-scheduler-periodic-trigger) upgrade sequence |
| Management API rejects the root credential | `Machine management API returned HTTP 401`; the bundle holds `APP_API_KEY_ROOT_KEY`, but the serving instances started from a bundle version without it or with another value | `CAP-ACCESS-authentication-authorization` rule 9 (Machine administration); [Cloud Scheduler registration](../runbooks/cloud-run-deployment.md#6-register-cloud-scheduler-periodic-trigger) root rotation and restart |
| Saved credential has no machine | `Stored scheduler credential has no machine; reconcile it explicitly`; `<service>-scheduler-credential` exists, but `GET /api/v1/machines` lists no `<service>-scheduler` | [Cloud Scheduler registration](../runbooks/cloud-run-deployment.md#6-register-cloud-scheduler-periodic-trigger) explicit rotation |
| Scheduler machine changed | `Scheduler machine is inactive or has unexpected scopes; refusing to change it`; the machine's `is_active` is `false` or its `scopes` differ from `autohub:dispatch` | `CAP-ACCESS-authentication-authorization` rule 9 (Machine administration) |
| Saved key is unusable | `Stored scheduler key is invalid, expired, or revoked; rotate it explicitly` or `Stored scheduler secret does not match its key ID`; the saved `key_id` is missing from the machine's keys, has `revoked_at` or a past `expires_at`, or the saved `key` lacks that key's prefix | [Cloud Scheduler registration](../runbooks/cloud-run-deployment.md#6-register-cloud-scheduler-periodic-trigger) explicit rotation |
| Key history without a saved secret | `Scheduler key history exists without a saved secret`; the machine lists keys, but `<service>-scheduler-credential` does not exist | [Cloud Scheduler registration](../runbooks/cloud-run-deployment.md#6-register-cloud-scheduler-periodic-trigger) lost-issuance reconciliation |
| Newly issued key not saved | `Could not save scheduler secret; the newly issued key was revoked`, or `Secret save and cleanup failed; revoke key <key-id> manually` when revocation also failed and the named key remains active | [Cloud Scheduler registration](../runbooks/cloud-run-deployment.md#6-register-cloud-scheduler-periodic-trigger) key revocation; [IAM permissions](../runbooks/cloud-run-deployment.md#4-service-account-iam-permissions) |
| A cloud call fails | `gcloud <group> <command> failed; inspect permissions and resource state`; the message names the `gcloud` group, such as `secrets`, `scheduler` or `run` | [Required APIs](../runbooks/cloud-run-deployment.md#12-enable-required-apis) and [IAM permissions](../runbooks/cloud-run-deployment.md#4-service-account-iam-permissions) for that group |
| No usable service URL | `A deployed HTTPS service URL is required`; `--url` was omitted or not `https://`, and service discovery returned no URL | [Cloud Run service deployment](../runbooks/cloud-run-deployment.md#53-deploy-cloud-run-service), then rerun provisioning with `--url` |

The generic `Scheduler provisioning failed; inspect deployment state` replaces any unexpected exception, such as a
network failure or an unparsable secret. For it, and for evidence that matches no row, rerun `just provision-scheduler`
against the same project and service and route the first sanitized message it prints; never replace a saved
credential or key to clear an unexplained refusal.

## Normal-state observation

Provisioning prints `Scheduler configured with machine <machine-id>; credential saved in <service>-scheduler-credential`.
After the next external tick, `GET /api/health/deep` reports `scheduler` `ok` with a current `last_tick_at`
(`CAP-EXEC-scheduling-maintenance` §4). A stale trigger after that point belongs to the
[trigger diagnosis](../runbooks/operator-notices.md#check-whether-the-trigger-is-firing), not to this routing.

## Authority boundary

The helpers do not report which bundle version a running instance loaded, so the HTTP `401` row is inferred from
the bundle and the instance start time. Cloud Scheduler job delivery, Secret Manager access policy and Cloud Run
revision health belong to Google Cloud. A completed provisioning run does not show that a tick reached the service.

## Update triggers

- `CAP-ACCESS-authentication-authorization` rule 9 or its machine administration interface changes.
- `CAP-EXEC-scheduling-maintenance` §4 changes the `GET /api/health/deep` scheduler fields.
- A refusal message, the credential shape `{machine_id,key_id,key}` or the secret names change in
  [provision-scheduler.py](../../scripts/provision-scheduler.py) or
  [setup_secrets.sh](../../docker/helper/setup_secrets.sh).
- [run_hub.sh](../../docker/run_hub.sh) changes how migrations run before the server starts.
