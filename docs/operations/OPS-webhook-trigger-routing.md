---
id: OPS-webhook-trigger-routing
title: "Missed webhook trigger diagnosis and routing"
status: active
summary: "Routes a GitHub event or @auto-run mention that did not enroll or advance a PR run to its owner through GitHub's delivery response, the stored delivery outcome, queue callbacks and the scheduler trigger; GitHub delivery and queue infrastructure stay outside Hub evidence."
related_capabilities:
  - CAP-PR-webhook-advancement
  - CAP-PR-pull-request-delivery
related_usecases:
  - UC-deliver-pull-request
---

# [OPS-webhook-trigger-routing] Missed webhook trigger diagnosis and routing

An `@auto-run` mention or a PR event produced no new run and no visible progress. Hub acknowledges an
authenticated delivery before it processes it, and records expected refusals as a `processed` delivery, so a 202
response in GitHub and a `processed` status in Hub both look healthy while no run exists. Some outcomes leave no
`failure_detail` at all. Repeating the enrollment request or redelivering from GitHub before identifying the stored
delivery does not tell these cases apart (`CAP-PR-webhook-advancement` §1, §3).

## Routing

**Operations → Webhook deliveries** (`UX-webhook-deliveries`) and `GET /api/v1/github-webhook-deliveries` list
deliveries with `status` (`received`, `retrying`, `processed`, `failed`), `attempts`, `auto_run`, the requested
catalog and `failure_detail`; filter by `repository` or `noteworthy=true`. GitHub's **Recent Deliveries** view of
the repository webhook shows the HTTP response Hub returned for each delivery ID.

| Symptom or state | Discriminating evidence | Next useful owner |
| --- | --- | --- |
| GitHub never sent the event | GitHub's Recent Deliveries has no entry for the event, and Hub lists no matching delivery | The repository webhook's event selection and URL in [Post-deployment verification](../runbooks/cloud-run-deployment.md#7-post-deployment-verification--integration); `CAP-PR-webhook-advancement` §2 places GitHub delivery out of scope. |
| Hub refused intake | GitHub shows HTTP 401 (signature mismatch), 503 (`GITHUB_WEBHOOK_SECRET` unset) or 400 (missing headers or a non-object body), and Hub lists no delivery for that ID | `CAP-PR-webhook-advancement` §3 rule 1 and §4; the webhook secret in [Post-deployment verification](../runbooks/cloud-run-deployment.md#7-post-deployment-verification--integration). |
| Redelivery did nothing | GitHub shows HTTP 202 with `status: duplicate` for a delivery ID Hub already stored | `CAP-PR-webhook-advancement` §3 rule 2 and the scheduler replay boundary in §4; [Diagnose a missed webhook trigger](../runbooks/operator-notices.md#diagnose-a-missed-webhook-trigger). |
| Trigger mention not recognized | The delivery is stored without the `@auto-run` badge: the text came from an ordinary Issue comment, an edited or deleted comment, or another event that supplies no trigger text | `CAP-PR-webhook-advancement` §4 (trigger text sources); enroll the PR through `UX-enroll-pull-request`. |
| Trigger ignored by project settings | `status` `processed`, `@auto-run` badge, no `failure_detail`, no run for the PR; no enabled project matches the repository, or the project's `@auto-run` enrollment is off | `CAP-PR-webhook-advancement` §3 rule 8; `UX-project-settings` for the project's `@auto-run` enrollment and enabled state. |
| Enrollment refused | `status` `processed`, `failure_detail` starts `Enrollment skipped:` | `CAP-PR-webhook-advancement` §3 rule 10; `CAP-PR-pull-request-delivery` owns the enrollment refusal named after the prefix. |
| Run enrolled but not yet dispatched | `status` `processed`, `failure_detail` starts `Enrolled; first dispatch deferred:` | The new run through `UX-run-page`; `CAP-PR-pull-request-delivery` owns the deferral reason, and the scheduler dispatches the run once it clears. |
| Advance left to the current lease holder | `status` `processed`, `failure_detail` starts `Advance deferred:` | `CAP-PR-webhook-advancement` §3 rule 10; the existing run through `UX-run-page`, where polling continues advancement. |
| Processing never completed | `status` `received` more than two minutes after arrival; Cloud Tasks shows failing callback attempts (for example HTTP 401 `Invalid task signature`), or the queue is unset and the in-process pass was lost | [Diagnose a missed webhook trigger](../runbooks/operator-notices.md#diagnose-a-missed-webhook-trigger) and [queue provisioning](../runbooks/cloud-run-deployment.md#61-webhook-processing-queue-cloud-tasks-recommended); `CAP-PR-webhook-advancement` §3 rules 4 to 6 and 12. |
| Replay is not running | `received`, or `failed` with `@auto-run`, stays unchanged with `attempts` below 2 within 24 hours of arrival, and System › Health shows the scheduler trigger as Stopped or Never fired | [Check whether the trigger is firing](../runbooks/operator-notices.md#check-whether-the-trigger-is-firing); `CAP-PR-webhook-advancement` §4, Scheduler replay boundary. |
| Processing failed | `status` `failed`, `failure_detail` `Webhook processing failed`; the application log carries `Processing GitHub webhook delivery <delivery_id> failed` with the exception | [Logs and expired history](../runbooks/operator-notices.md#logs-and-expired-history); `CAP-PR-webhook-advancement` §3 rule 11. |
| Replay exhausted or stranded | A `failed` `@auto-run` delivery with `attempts` 2, an `error` notice that the `@auto-run` could not be handled after a retry, a delivery older than 24 hours, or a delivery left `retrying` after its replay pass ended | `CAP-PR-webhook-advancement` §4, Scheduler replay boundary, which no longer selects it; enroll the PR through `UX-enroll-pull-request` (`UC-deliver-pull-request`). |

Find the delivery by repository and time before any other action, because its `status` and `failure_detail`
already separate most rows; consult GitHub's Recent Deliveries only when Hub lists no delivery. For evidence that
matches no row, follow [Diagnose a missed webhook trigger](../runbooks/operator-notices.md#diagnose-a-missed-webhook-trigger)
with the delivery ID.

## Normal-state observation

After the owner's action, GitHub shows HTTP 202 `accepted` for the next delivery, Hub lists it as `processed` with
no `failure_detail` or with an expected deferral, and the PR has an active run visible through `UX-run-page`.
`CAP-PR-webhook-advancement` owns intake and processing outcomes; `CAP-PR-pull-request-delivery` owns the run's
subsequent progress.

## Authority boundary

A `processed` delivery or an accepted callback is not evidence that enrollment, dispatch, CI or merge completed
(`CAP-PR-webhook-advancement` §1). Polling advances an already enrolled run but cannot reconstruct an enrollment
whose delivery was never stored. Hub retains no raw payload, so the delivery list cannot show the original
comment text. `CAP-EXEC-scheduling-maintenance` owns the 90-day delivery retention.

## Update triggers

- `CAP-PR-webhook-advancement` §3 rules 1, 2, 8 and 10 to 12, or the §4 trigger text sources or Scheduler replay
  boundary, change.
- The delivery `status` values or the `failure_detail` prefixes written in
  [usecases.py](../../modules/hub/app/features/project_management/github_webhooks/usecases.py) change.
- The intake responses in
  [api.py](../../modules/hub/app/features/project_management/github_webhooks/api.py) change.
