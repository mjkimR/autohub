# Recorded production verification — 2026-10-02

This report consolidates live checks from 2026-09-21 through 2026-10-02 against
Cloud Run and `mjkimR/test-sandbox`. The last recorded production baseline is
**2026-10-02**, revision `autohub-00015-4l4`, DB schema `autohub`; this is not a
check of the currently serving deployment. See [delivery status](../../../operations/deployment-status.md)
for the distinction between local implementation, production evidence and rollout gaps.
GitHub links provide external evidence; Hub run history may expire under retention.

## PR automation

| Date | Live evidence | Observed result |
| --- | --- | --- |
| 2026-09-21 | PRs [#4](https://github.com/mjkimR/test-sandbox/pull/4), [#5](https://github.com/mjkimR/test-sandbox/pull/5), [#6](https://github.com/mjkimR/test-sandbox/pull/6) | Codex implementation, push, current-head CI and automatic merge; concurrency limit 1 held subsequent work. |
| 2026-09-22 | PRs [#7](https://github.com/mjkimR/test-sandbox/pull/7), [#8](https://github.com/mjkimR/test-sandbox/pull/8); [#8 repair CI](https://github.com/mjkimR/test-sandbox/actions/runs/35673910385) | One `ci-fix` each, followed by automatic merge; #8's actual request carried the failing assertion/traceback without weakening verification. |
| 2026-09-22 | Preparation [#9](https://github.com/mjkimR/test-sandbox/pull/9), target [#10](https://github.com/mjkimR/test-sandbox/pull/10), [repair CI](https://github.com/mjkimR/test-sandbox/actions/runs/35675447054) | One `conflict-fix` retained both changes and merged automatically. |
| 2026-09-22 | Draft PR [#11](https://github.com/mjkimR/test-sandbox/pull/11), [final CI](https://github.com/mjkimR/test-sandbox/actions/runs/35676475973) | Draft and missing current-head CI held merge; returning to Draft withdrew approval; final Ready plus passing CI merged without an agent request. |
| 2026-09-22 | PR [#12](https://github.com/mjkimR/test-sandbox/pull/12), [CI](https://github.com/mjkimR/test-sandbox/actions/runs/35677259553) | With its webhook disabled, an already registered run merged through polling without manual advancement or new deliveries; webhook was restored. |
| 2026-09-22 | Jules [report session](https://jules.google.com/session/15043012283364374433), [task session](https://jules.google.com/session/7977738327420503966), PR [#13](https://github.com/mjkimR/test-sandbox/pull/13) | Report retained without PR/run creation; task PR automatically enrolled and merged; both sessions returned capacity. |

Recorded revisions: #7 used `autohub-00008-xtl`; #8–#12 used
`autohub-00009-mqv`; Jules and connection checks used `autohub-00010-x9c`.
Catalog creation also returned 201, duplicate key 409 and invalid key 422.

## Work plans

| Date | Live evidence | Observed result |
| --- | --- | --- |
| 2026-09-23 | PRs [#18](https://github.com/mjkimR/test-sandbox/pull/18), [#20](https://github.com/mjkimR/test-sandbox/pull/20); Plan Issue [#17](https://github.com/mjkimR/test-sandbox/issues/17) | Dependent Item started only after its predecessor merged; Plan completed and mirrored Issues closed. |
| 2026-09-23 | Plans [#21](https://github.com/mjkimR/test-sandbox/issues/21), [#23](https://github.com/mjkimR/test-sandbox/issues/23) | Pause held unstarted work; revoke also worked for a Plan blocked by a revoked dependency; no PR/run was created. |
| 2026-09-23 | PRs [#25](https://github.com/mjkimR/test-sandbox/pull/25), [#29](https://github.com/mjkimR/test-sandbox/pull/29); Plan Issue [#26](https://github.com/mjkimR/test-sandbox/issues/26) | Registration started work in the response; dependent work started 2 seconds after #25 merged; Plan completed 3 seconds after #29 merged, without manual advancement. |
| 2026-09-28 | PR [#31](https://github.com/mjkimR/test-sandbox/pull/31), Issues [#32](https://github.com/mjkimR/test-sandbox/issues/32), [#33](https://github.com/mjkimR/test-sandbox/issues/33) | Webhook created mirrors before the next tick, but the Item closed only at the tick, exposing parent-ordering delay. |
| 2026-09-28 | PR [#34](https://github.com/mjkimR/test-sandbox/pull/34), Issues [#35](https://github.com/mjkimR/test-sandbox/issues/35), [#36](https://github.com/mjkimR/test-sandbox/issues/36) | After correction, Plan mirror preceded Item mirror; both closed 3–6 seconds after merge without waiting for a tick. |

The 09-23 immediate-execution check used `autohub-00001-spj` after service
recreation. Logs recorded webhook 202 responses followed by Cloud Tasks callback
204 responses; a later 20-request concurrency check passed on `autohub-00002-rcl`.
The two 09-28 checks used `autohub-00004-96p` and `autohub-00006-dz7` respectively.
The first 09-23 check preceded service recreation; its exact revision was not recorded.

## Connection and question flow

On 2026-09-22, Codex [#14](https://github.com/mjkimR/test-sandbox/pull/14) and
Jules [#15](https://github.com/mjkimR/test-sandbox/pull/15) passed connection checks,
closed without merging and deleted all three test branches. Repeated requests
returned the same ID, concurrent new starts returned 409, and development-run
enrollment returned 422 before and after cleanup. Main stayed at
`6c68c88373e01b4c04284ce1b464f6734e62278b` (#13's merge).

On 2026-10-01, a fresh `autohub` schema and `personal-codex` catalog (concurrency 1)
were checked through MCP. Connection PR [#41](https://github.com/mjkimR/test-sandbox/pull/41)
passed at head `9bd4a6a3`. Plan `1dcdbd8b` and its Items were unchanged by duplicate
registration; [#42](https://github.com/mjkimR/test-sandbox/pull/42) merged before
[#46](https://github.com/mjkimR/test-sandbox/pull/46) started. The latter question
was detected after the author-normalization fix, answered through `runs_answer`
and resumed through `runs_resume`; duplicate calls returned the same answer and
resume receipt (revision 6). Codex received the answer and merged the implementation;
the Plan completed. Connection/Plan checks used `autohub-00012-9gf`; the corrected
question flow used `autohub-00013-l4q`.

The live run exposed an invalid Codex-environment `GH_TOKEN`; replacing it restored
connection success. It also exposed reply-author handling and no-push/capacity
problems corrected in `dc8fc8b`, `74f8f53` and `fa9bea7`. The question had remained
undetected for over 40 minutes before correction; detection and resumed dispatch
then followed the 5-minute tick, not an immediate-delivery claim.

## Stop and recovery

On 2026-10-02, Plan `20b5822d` was checked through MCP with `personal-codex`
(concurrency 1). The check began on `autohub-00013-l4q` and resumed on
`autohub-00014-hrs` after fix `746959d`.

- Paused Run [#47](https://github.com/mjkimR/test-sandbox/pull/47) received a Codex
  push and passing CI without Hub merging. Its first resume resent completed work
  and blocked; this PR was manually merged before the run completed.
- After the fix, paused [#53](https://github.com/mjkimR/test-sandbox/pull/53) resumed
  to `awaiting_ci` after an external push and merged without another request.
  Plan pause held its next Item through ticks; Plan resume started it in the request.
- Canceled [#54](https://github.com/mjkimR/test-sandbox/pull/54) still received an
  external push, was closed without merging, and its Item became `canceled` on the
  next tick. Revoking the original Plan left its unstarted Item `revoked`.
- Replacement Plan `f2adc4f1` linked the original Plan/Item/Run/PR identities and
  completed with [#55](https://github.com/mjkimR/test-sandbox/pull/55) and
  [#59](https://github.com/mjkimR/test-sandbox/pull/59). Successful original work was
  not repeated; the original Plan remained `revoked` rather than becoming successful.

## Google authentication

The recorded 2026-10-02 baseline includes real-account validation in both `query`
and `form_post` callback modes: pending signup had no tokens/access; approval
allowed login; suspension rejected API calls and refresh; reactivation required
fresh login and did not revive old tokens. Regular users could not administer
accounts, and the bootstrap account could not be disabled or demoted. Existing
local superadmin login also passed. The retained record gives no separate date,
revision or external run link for these checks. The repeatable procedure remains
in [Google authentication](../../../operations/access.md#live-validation).

## Limitations

- These checks do not prove discovery of a PR whose registration trigger never
  arrived. Draft intermediate-state observations and connection-test progression
  used manual observation/advance; connection cleanup used the dispatcher. Jules
  task startup used one manual dispatcher call; later collection and merge were automatic.
- Not induced live: Telegram, Jules quota exhaustion/429, required reviews/branch
  protection, connection-test timeout/lost response/authentication failure,
  cancellation/manual-cleanup recovery and final merge defense for an already
  enrolled connection-test run, failed-Item retry, Plan revision conflicts, or Plans
  mixed with failing CI. Invalid Codex `GH_TOKEN` diagnosis above is separate from
  deliberate connection-test authentication-failure coverage.
- Follow-up revision `autohub-00011-xpl` replaced two stopped connection schedules
  with shared maintenance and recorded a successful 13:55 KST tick/checkpoint;
  no rows were expired, so actual expired-row deletion was not verified.
- Retained artifacts: merged `autohub/work/*` branches, completed session/run/PR
  links, the normalized sandbox dispatcher and inactive credential-free catalog
  `canary-api-20260922` (unassigned; no deletion API). Two Jules canary schedules and
  the old catalog sync were removed; connection-test branches were deleted.
- Jules report source-message key and the reason for null task `result_summary`
  were not established. The Draft observation's transient 409 was not diagnosed.
  A cross-Plan dependency error omitted validation details during the 10-02 run;
  the later app-common correction was `a36b829` and was not reverified by this run.
