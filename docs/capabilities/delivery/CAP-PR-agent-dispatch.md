---
id: CAP-PR-agent-dispatch
title: PR Agent Dispatch and Recovery
summary: "Auto Hub renders self-contained Codex PR mentions and reconciles each persisted delivery through trusted comment identity. Push, quota and watchdog observations keep provider acknowledgement separate from completed implementation."
area: delivery
status: active
usecases:
  - UC-deliver-pull-request
entrypoints:
  - modules/hub/app/features/project_management/pipeline_runs/dispatch.py
  - modules/hub/app/features/project_management/pipeline_runs/adapters/codex_github_mention.py
  - modules/hub/app/features/project_management/pipeline_runs/usecases/delivery.py
  - modules/hub/app/features/project_management/pipeline_runs/usecases/implementation.py
---

# [CAP-PR-agent-dispatch] PR Agent Dispatch and Recovery

## 1. Summary

An attempt's immutable request can have several numbered deliveries. Each
delivery is one intended top-level PR mention, recovered by its marker and the
connector author's identity. `UC-deliver-pull-request` uses this adapter;
`CAP-PR-pull-request-delivery` owns Run admission, control and merge decisions.

## 2. Scope & Boundary

- **In-Scope**: mention rendering, hidden-text filtering, delivery identity,
  reconciliation, trusted reply observation, push evidence and bounded silent/
  no-push handling for the `codex-github-mention` adapter.
- **Out-of-Scope**: the provider performs implementation; `CAP-AGENT-catalog-admission`
  owns account quota/capacity policy; `CAP-PR-operator-decisions` owns question
  interpretation; `CAP-PR-ci-observation` owns CI evaluation.
- **Scope Excluded**: a provider task-status API, selecting the provider's model
  through mention text, remote cancellation, arbitrary GitHub comment authors as
  trusted signals, and a built-in `codex-action` fallback adapter.

## 3. Business Rules & Policies

1. **Framed mention**: WHEN rendering a delivery, Hub MUST place one leading `@codex` task mention before the body and its attempt/kind/delivery/head marker at the end. Check: [`test_dispatch.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/test_dispatch.py), `TestCodexMentionComment.test_starts_with_the_mention_and_ends_with_the_marker`.
2. **Self-contained request**: WHEN rendering task or fix work, Hub MUST include the retained task/linked-Issue context, request instructions and explicit same-branch push guidance in that comment. Check: [`test_dispatch.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/test_dispatch.py), `TestCodexMentionComment.test_is_self_contained_with_task_linked_issues_and_push_command` and `test_fix_instructions_and_evidence_reach_the_comment`.
3. **Hidden-marker filtering**: WHEN rendering task text, Hub MUST remove complete hidden HTML comments and defuse unterminated comment openers. Check: [`test_dispatch.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/test_dispatch.py), `TestCodexMentionComment.test_hidden_html_comments_cannot_forge_a_marker`.
4. **No extra trigger**: IF task text or saved request instructions contain another prohibited Codex mention, THEN rendering MUST refuse that text. Check: [`test_dispatch.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/test_dispatch.py), `TestCodexMentionComment.test_task_text_that_mentions_codex_is_refused` and `test_instructions_cannot_add_another_codex_mention`.
5. **Approval remains human-owned**: WHEN rendering any implementation/fix delivery, Hub MUST instruct the agent to preserve PR draft status. Check: [`test_dispatch.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/test_dispatch.py), `TestCodexMentionComment.test_saved_requests_receive_the_operator_approval_rule_on_redelivery`.
6. **Trusted reconciliation**: WHEN reconciling a delivery marker, Hub MUST adopt only a matching comment authored by the connector account. Check: [`test_dispatch.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/test_dispatch.py), `TestGitHubMentionDelivery.test_reconciliation_uses_only_the_connector_accounts_marker`.
7. **Durable uncertain delivery**: IF the process stops before posting or loses the accepted post response, THEN Hub MUST recover the same planned delivery before creating another comment for it. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `test_pre_post_crash_reuses_the_planned_delivery_on_restart` and `test_post_response_crash_is_reconciled_without_a_duplicate_mention`.
8. **Authorization before write**: IF the dispatcher's lease was replaced before posting, THEN Hub MUST reject the stale dispatcher without posting its mention. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `test_expired_dispatcher_cannot_post_after_another_worker_takes_over`.
9. **Push wins**: WHEN an ordinary Run's PR head moved after the delivered request, Hub MUST enter CI observation before no-push/watchdog/quota-reply processing. Check: [`test_lifecycle.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/usecases/test_lifecycle.py), `test_pushed_head_wins_over_watchdog_and_quota_replies`.
10. **No-push reply**: IF a non-quota Codex reply has no resulting push after five minutes and the latest delivery is not a silent retry, THEN Hub MUST block the ordinary Run for operator investigation. Check: [`test_lifecycle.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/usecases/test_lifecycle.py), `test_codex_reply_without_push_blocks_after_grace`.
11. **Silent retry boundary**: IF an ordinary Run has no push two hours and five minutes after its latest delivery, no silent retry exists for that attempt and no earlier question/quota/no-push-reply branch applies, THEN Hub MUST prepare one delivery with cause `silent`. Check: [`test_lifecycle.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/usecases/test_lifecycle.py), `test_silent_watchdog_uses_an_exact_fixed_clock`.
12. **Account quota brake**: WHEN a trusted quota reply is observed without a push, Hub MUST record the account-wide catalog hold and a quota delivery without imposing a per-Run quota-retry cap. Check: [`test_lifecycle.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/usecases/test_lifecycle.py), `test_quota_reply_sets_a_global_catalog_hold_without_a_run_retry_cap`.
13. **Single catalog accounting**: WHEN a delivery is retried under its existing identity, Hub MUST count it once in the catalog dispatch ledger. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `test_a_retried_delivery_is_counted_once_in_the_catalog_ledger`.

## 4. Interfaces & Data Contracts

The adapter posts a top-level issue comment through GitHub's
`POST /repos/{owner}/{repo}/issues/{pull_number}/comments`, not a review-thread
reply. Its final hidden marker is:

```text
<!-- hub-attempt:<idempotency-key> kind=<implementation|ci-fix|conflict-fix> delivery=<positive-number> head=<prepared-head-sha> -->
```

The immutable `ImplementationRequest` contains `repository`, PR snapshot,
instructions, kind and `correlation_marker`. The prompt includes the bound
question marker defined by `CAP-PR-operator-decisions`; it avoids selecting the
separate review mode. Deliveries retain their number, cause (`initial`, `silent`,
`quota`, `resume`), external comment ID and posting time. Causes describe retry
intent; a process restart alone does not advance their number.

Before adapter I/O, Hub persists the attempt and planned delivery under the Run
lease. It resolves the connector's authenticated login, searches matching
comments and posts only after the authorization callback passes. Reconciliation
includes correlation marker, kind and delivery number. Only a valid returned
comment ID and creation time confirm publication; malformed timestamps are not
replaced by recovery time. An uncertain timeout leaves the delivery recoverable.

Reply collection accepts `chatgpt-codex-connector` after normalizing a `[bot]`
suffix, with a parseable timestamp no earlier than the delivery. Replies remain
observations, not proof of completed implementation. Hub does not establish who
pushed a changed head; a human push can satisfy the same implementation signal.
The quota matcher recognizes `usage limit`, `rate limit` or `usage settings`
wording only from that normalized connector author.

### Ordinary-run waits

Observation handles a closed PR or changed head first, then trusted questions,
quota replies, no-push reply grace and finally the silent deadline. Later rows
below do not override an earlier applicable question/quota/reply transition.

| Condition | Result |
| --- | --- |
| Current PR head differs from delivered head | Enter `awaiting_ci` before reply/watchdog handling |
| Trusted non-quota reply without a push after five minutes; latest cause is not `silent` | Enter `blocked` with the reply-investigation reason |
| No push after 2h5m from latest delivery; no silent retry in this attempt | Prepare the next `silent` delivery |
| No push after another 2h5m and a silent retry already exists | Enter `blocked`; a new reply does not reset the delivery timer |
| Trusted quota reply without a push | Record catalog policy state and prepare `quota` delivery; wait for admission |

The second-silent-expiry branch is source-defined in `ImplementationProgress`;
the named fixed-clock example tests the first-retry boundary. A silent retry can
overlap a slow first provider task; the adapter does not claim exactly-once
provider execution. Native SDD progress uses its own workflow evidence rather
than these ordinary no-push/watchdog transitions.

CI-fix request evidence carries at most three failed-job excerpts of at most
1,000 characters each. Selection removes timestamps/ANSI, redacts known secret
patterns and favors diagnostics with nearby context before truncation. A log
read failure does not prevent the repair transition. Redirected log download
does not forward connector authorization/cookie headers to the log host.

## 5. Source and verification evidence

Inspected source: [`dispatch.py`](../../../modules/hub/app/features/project_management/pipeline_runs/dispatch.py),
[`codex_github_mention.py`](../../../modules/hub/app/features/project_management/pipeline_runs/adapters/codex_github_mention.py),
[`delivery.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/delivery.py),
[`implementation.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/implementation.py),
[`ci.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/ci.py)
and [`logs.py`](../../../modules/hub/app/features/project_management/pipelines/logs.py).
Additional inspected checks: [`test_logs.py`](../../../modules/hub/tests/unit/features/project_management/pipelines/test_logs.py),
[`test_ci_log_evidence.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_ci_log_evidence.py)
and `TestGitHubMentionDelivery.test_failed_job_log_is_bounded_and_redacted` in the
linked dispatch tests. These are source/test inspections, not fresh execution or
live provider assurances. Repository provider setup and canary actions belong in
operator procedures, not in this protocol contract.
