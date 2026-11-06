---
id: SPEC-decision-notifications
title: Notify operators about actionable delivery decisions
summary: "Deliver decision-focused notices with exact owner links, project and kind subscriptions, and bounded digests while preserving current decision authority."
status: completed
created: 2026-11-06
related_capabilities: [CAP-NOTIFY-operator-notifications, CAP-PR-operator-decisions]
related_usecases: [UC-resolve-run-question]
workflow: sdd-spec-feature
---

# [SPEC-decision-notifications] Notify operators about actionable delivery decisions

## 1. Problem Statement & Motivation

Handed off from proposal PROP-decision-notifications on 2026-11-06.
- **Preserved Materials**: `docs/materials/2026-11/20261106-decision-notifications`
- Target Docs Blueprint: `PROP-decision-notifications-target` (Living Spec targets for this plan and reconcile.md)

### 1. Background & Hypothesis

`CAP-NOTIFY-operator-notifications` supplies global operator-owned Telegram channels. `CAP-PR-operator-decisions` supplies a transactional, indexed decision discovery projection. Neither capability promises that a Telegram chat participant is a Hub account. Current authenticated human accounts share project visibility; this feature preserves that model rather than inventing project ACLs or per-chat recipient identity.

The operator explicitly enables selected decision notices on a trusted destination, receives minimal metadata and opens the exact authenticated owner review. The hypothesis is that this removes repeated inbox polling without making transport delivery an execution or authorization event. `docs/materials/2026-11/20261106-decision-notifications/owner-seams.md` records source inspection; no product tests or live delivery ran in Planning.

Priority is second after `SPEC-mcp-delivery-tools`, before `PROP-work-plan-templates`; none is a prerequisite of this feature. Parallel Planning and implementation are possible with the future file coordination below.

## 2. User Stories

- As an operator, subscribe a trusted destination to relevant pending decisions and open the exact authenticated review.
- As an operator, distinguish accepted, refused and unknown notice delivery and explicitly recover uncertain commands.

## 3. Non-Goals

- **Scope Excluded**: inbound Telegram decisions, implicit approval/resume, new project ACLs, automatic uncertain resend, Jules/SDK work, monitoring and deployment.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Disabled defaults

- **Given** a migrated or never-configured channel.
- **When** read or maintained.
- **Then** decision notices remain disabled and legacy behavior is unchanged.

### [AC-02] Subscription gates

- **Given** trusted project/kind settings and destination generation.
- **When** saving or admitting.
- **Then** current severity/project/channel gates and exact actor-bound replay apply; stale destination changes refuse.

### [AC-03] Atomic admission

- **Given** concurrent workers inspect one generation.
- **When** admitting send.
- **Then** one durable leased attempt wins and channel generations deduplicate independently.

### [AC-04] Bounded digest

- **Given** more than ten eligible rows or long metadata.
- **When** formatting and sending.
- **Then** at most ten complete links fit 3500 characters and omitted rows remain pending.

### [AC-05] Uncertain delivery

- **Given** timeout, expired lease or acknowledgement persistence failure.
- **When** maintenance repeats.
- **Then** sending becomes unknown without automatic resend; explicit resend is reviewed and request-idempotent.

### [AC-06] Exact navigation

- **Given** a notice selection outside current inbox pages.
- **When** opening after authentication.
- **Then** an indexed exact lookup then existing owner review selects only matching key/fingerprint; stale/missing targets never substitute.

### [AC-07] Destination rotation

- **Given** credential/chat or subscription changes race admission.
- **When** saving or ticking.
- **Then** destination generation is checked even at revision zero; future admissions stop and admitted sends may finish.

### [AC-08] Fair retention

- **Given** old accepted/unknown generations and many subscriptions.
- **When** compacting and rotating.
- **Then** dedupe remains and bounded cursor progress lets other subscriptions advance.

### [AC-09] Command recovery

- **Given** lost save/resend responses or another actor.
- **When** reading or replaying exact request.
- **Then** original result stays separate from current state; missing proof stays unknown and wrong actor receives404.

### [AC-10] Login restoration

- **Given** password/Google completion, cancellation, TTL expiry or denied storage.
- **When** returning from sign-in.
- **Then** only successful approved authentication restores one validated same-origin selection; no payload/credentials or arbitrary redirect is stored.

## 5. Carried Proposal Notes

Sections of the proposal that did not map to a spec section. Trim or promote them while drafting; they are not contracts.

### 2. Technical Spike Questions

- **Q1 resolved**: Use persisted `DecisionEntry.key` plus `fingerprint`, not run revision or title, as the generation identity. Notice admission requires the exact row still actionable and owner run nonterminal. Native state is last-observed evidence, never a fresh remote evaluation.
- **Q2 resolved**: One optional revisioned decision subscription belongs to each existing global Notification channel. Explicitly choose project IDs or All current and future projects, nonempty decision kinds and a trusted destination confirmation. Existing channels default to decision notices off. Human authentication and project existence follow existing policy; no Telegram recipient ACL is claimed.
- **Q3 resolved**: Use bounded polling plus separate notice/attempt records. Immediate means next eligible maintenance pass. Digest uses a fixed 15-minute interval. Confirmed transport acceptance deduplicates; unknown send outcomes require explicit resend review and may duplicate remotely.
- **Q4 resolved**: Link to the configured Hub origin at `/decisions?decision_key=<encoded>&decision_fingerprint=<encoded>`. Preserve the exact identity through password and Google sign-in as specified below. Only after authentication resolve the exact entry and use the existing owner review operation; its native observation/CAS effects and errors remain unchanged.

#### Compared alternatives

| Option | Advantage | Cost / risk | Disposition |
| --- | --- | --- | --- |
| A: poll current persisted decision discovery into channel-owned delivery receipts | No changes to decision mutation transactions; bounded query and recoverable delivery admission | Observed decisions may disappear before a scan; no guaranteed latency | Recommended |
| B: enqueue notice events inside every owner mutation transaction | Captures transient generations and tighter creation correlation | Wider coupling to every owner path; transport is still nontransactional | Rejected for this scope |
| C: add only deep links to existing run-stop broadcasts | Smallest change | No project/kind subscription, digest or generation dedupe | Insufficient |

`ADR-decision-notice-delivery` records A. No business-only question remains. Limits/defaults and channel-level trust are Host-choice assumptions within the requested feature; their exact consequences go to plan-accept.

### 3. Proposed Design & Impact

#### Subscription and compatibility

Add strict `DecisionSubscription` settings per channel: `revision`, `enabled` (default false), `project_scope` (`selected` or `all`), distinct existing project UUIDs for selected scope, a nonempty subset of the six `DecisionKind` values, `mode` (`immediate` or `digest`), and a validated `review_origin`. Empty selected projects is invalid when enabling. All scope explicitly covers future projects. `review_origin` is an HTTPS origin with no credentials, path, query or fragment; loopback HTTP is allowed for local use. It is only used to construct links; Hub never fetches it. Display the resulting destination origin before enablement. Existing settings APIs, legacy notices and explicit channel tests retain their behavior.

Candidate authenticated routes under `/api/v1/notification-channels/{channel_id}`: `GET /decision-subscription`, `PUT /decision-subscription`, `GET /decision-notices?cursor&limit`, and `POST /decision-notices/{notice_id}/resend`. Add `GET /decision-requests/{request_id}?operation=subscription|resend` for exact command recovery. Subscription readback includes the current channel destination generation even before a subscription exists. PUT includes expected subscription revision, expected destination generation, request UUID and complete normalized settings; actor comes from the signed-in account, never the body. Keep channel/operation/request UUID receipts with authenticated actor binding so identical actor/payload replay returns its original result plus current settings; changed identity/payload returns 409. Unknown channel is 404, malformed settings 422 and stale revision 409. Exact replay lookup precedes all current revision/destination eligibility guards. Migration creates no enabled subscription or notices; GET returns disabled defaults/revision 0 and the actual current channel destination generation until first save. Exact receipt reads require the original actor under current human authentication: missing request on an accessible channel returns200 `record_state: unknown`, never definite failure; another actor cannot inspect the original receipt (404). A recorded response returns original immutable command result/attempt identity separately from current subscription, notice and attempt outcome. Receipt retention follows the channel lifetime independently of detailed attempt-history compaction, so later settings or history changes cannot erase proof of the original request. Receipts store no bot credential, answer or question text.

Channels stay global under existing signed-in-user policy. Saving a subscription confirms this chat is trusted for the selected project metadata; it grants no execution authority. Add a destination generation incremented only when chat ID or bot credential changes. Such a change disables decision notices until explicit review/re-enable; the generation increments on the channel even when no subscription row exists. Every enabling/editing PUT and reviewed resend carries the displayed expected destination generation. After exact replay handling, compare it under the same channel/subscription admission locks; mismatch returns409 without enabling or sending, and the UI reloads the actual destination and clears trust confirmation. Legacy generic notices remain governed by current channel settings. Channel enablement and `min_level` still apply: decision notices have warning severity, so error-only channels receive none. The UI discloses both effective gates before save.

#### Bounded discovery and admission

Use the current `DecisionDiscoveryRepository` bounded query through a notification-owned adapter; do not call `DecisionDiscoveryUseCase.review` during background work. This intentionally reads persisted observation only. No provider, GitHub, token or repository calls occur while collecting/formatting notices.

Each maintenance pass rotates through at most 4 enabled subscriptions with a durable UUID cursor, considers at most 100 discovery rows per subscription and admits at most one message per subscription. Use persisted per-subscription `(waiting_since,key)` scan checkpoints and wrap to the start after exhaustion. Advance the checkpoint by the final examined row, including already-notified or publication-pending rows, so those rows cannot trap the scan. Apply an overall45-second notification budget; cancellation after send admission leaves the retained attempt uncertain rather than restarting it. Add this helper after existing maintenance owners or under their remaining budget so notice failure does not prevent their progress. New generations before a cursor are discovered on a later rotation. No claim is made that decisions which vanish between observations are notified. Polling delay follows the existing shared maintenance scheduler, not a resident timer.

One decision notice identity is `(channel_id,destination_generation,decision_key,fingerprint)` with a unique database constraint. Settings revision changes do not resend previously accepted generations. Enabling or expanding a filter includes matching currently observed pending work; the review disclosure says so. Select only actionable rows with current project existence and nonterminal owner; before admitting a send, re-read all included exact generations and subscription/channel settings. A stale, resolved, wrong-filter or inaccessible row is suppressed without calling transport. Reappearing exact fingerprints retain their old accepted/unknown dedupe state; a different fingerprint is a distinct observed generation.

A digest window starts when the first eligible unnotified entry is retained, and becomes due 15 minutes later. Discovery and send rechecks use current filters, not stale text. Immediate batches are due on the next eligible pass. Build at most 10 entries and a 3,500-character message including warning prefix and links, below Telegram's 4,096-character boundary; never rely on transport truncation. Entries that do not fit remain pending for later batches, not acknowledged. Each message contains only decision kind, project name, PR number/run identity, ordinary waiting time or native First observed time, observation time and exact review links. Omit question/answer text, request payloads, credentials and unbounded provider errors. A link from this minimal notice still requires Hub authentication.

#### Delivery evidence and uncertain outcomes

Persist immutable message membership/payload and a `sending` attempt with a token and 60-second lease before network I/O. A compare-and-set under channel/subscription locks prevents overlapping workers admitting the same generation. Network work happens outside DB locks and uses the existing 10-second Telegram timeout. Revalidate the unexpired token before committing a result. An expired sending attempt becomes `unknown` and cannot be automatically resent. The original worker may not overwrite a later state after lease loss.

A structured transport result distinguishes `accepted`, proven pre-send/Telegram refusal, and `unknown` (timeout, connection error or missing persisted acknowledgement after possible acceptance). Add this outcome information for decision delivery without changing generic `Notifier.send` semantics or its exception behavior. Confirmed acceptance marks each included notice generation accepted; no single-channel success acknowledges another channel. Record safe failure codes and times, never raw credential-bearing URLs or response bodies. Proven refusal is retained as failed; no automatic reattempt is required in this scope. Explicit Send again creates a fresh attempt for the same retained notice only after current subscription/generation rechecks and operator review. Unknown sends require acknowledgement that the external message may be duplicated. Its request UUID/actor/payload replay never creates an extra attempt. Superseded generations cannot be resent; offer the current inbox instead.

Subscription disablement, deletion and filter/destination edits govern future send admissions. A message already durably admitted may finish; show that limit in the UI. Deleting a channel stops future sends and removes its subscription/notice state with existing channel lifetime. Within a retained destination generation, keep minimal dedupe evidence for the channel lifetime; pruning delivery history must not make accepted or unknown generations eligible again. Keep the latest 100 attempt histories per channel with bounded pagination; older attempts may be compacted to generation state plus last outcome/time. No decision/Run retention is extended by notification records; deleted owner records become unavailable rather than recreated.

#### Exact navigation and owner boundary

The inbox reads one URL selection after session restoration without depending on its current list page or filters. Add authenticated, read-only `GET /api/v1/pipeline-runs/decisions/selection?key&fingerprint`, returning the current matching `DecisionEntryRead` joined to its nonterminal run/current project. Use a direct indexed key lookup, never a scan through inbox pages or a decoded guess from the hashed key. Validate key length at most255 and a64hex fingerprint; missing/inaccessible owner/project is404 and a changed fingerprint is409. This query performs no remote call or inspection mutation. It uses the same current visibility policy as discovery. Reuse the existing response schema; expose the new route in generated pipeline-run types.

After lookup, call existing authenticated `POST /pipeline-runs/decisions/review` with that exact key/fingerprint and retain the returned Entry alongside its validated Run. A change between lookup and review is refused by existing owner guards. Those two server-validated objects select the same ordinary question or native request in the existing dialog, including when several questions share a run or the subject is outside loaded pagination. Native review may refresh and persist inspection under the existing predecessor CAS. Password sign-in renders in place and retains the notice query. Google sign-in leaves the app, so add a narrow notice-return helper under the auth/login UI parent. Immediately before its existing external redirect, retain only the validated key/fingerprint plus timestamp in this tab's sessionStorage under a dedicated key, for at most30minutes. Never store a general redirect URL, actor, mutation payload, answer or credential. Restore only the fixed same-origin `/decisions` route after successful approved Google exchange or password login; validate again, consume the stored pair once, and then run exact owner lookup/review. Cancellation, pending/rejected/suspended accounts, failed exchange and missing tokens never navigate into owner review; retain the pair only within its original TTL to support password fallback. Explicit Open inbox clears it. Expired/malformed/unavailable storage drops the return identity safely and explains that the operator can reopen the original notice; authentication itself must still complete. Full sign-out does not grant any stored selection authority, and no session-store or logout behavior is changed.

The link never conveys an actor, answer, approval or a resumable command. Missing/changed/inaccessible links display a generic unavailable/changed state with Refresh inbox; no replacement subject is opened automatically. Malformed selections are rejected locally without a mutation. Keep a landing status while inspecting; after a failed inspection, offer explicit Retry review and Open inbox. Keep native last-observed metadata distinct from fresh owner inspection.

#### Acceptance examples and Development verification

- **NOTICE-01**: Given a migrated existing channel, when read or ticked before explicit subscription enablement, then decision notices remain off and generic notice behavior is unchanged.
- **NOTICE-02**: Given a trusted subscription with project/kind and severity gates, when current exact actionable rows match, then only those rows can be admitted; changed filters, disabled channels and foreign/missing projects cannot leak content.
- **NOTICE-03**: Given two concurrent maintenance workers, when they encounter the same generation/channel, then one send admission wins; success on one channel does not acknowledge another.
- **NOTICE-04**: Given a digest with more entries than count/character bounds, when sent, then every included link is complete and omitted entries remain pending; stale generations are suppressed before send.
- **NOTICE-05**: Given transport timeout or accepted-send/persist failure, when the lease expires or maintenance repeats, then the generation remains unknown without blind POST retry. Explicit reviewed resend may duplicate; replay of its command adds no attempt.
- **NOTICE-06**: Given malformed or changed exact notice links, when opened after login or outside the first inbox page, then bounded exact-entry lookup and authenticated owner review alone can open; no automatic answer/approve/resume or replacement selection occurs.
- **NOTICE-07**: Given subscription disablement or credential rotation racing send admission, including a revision0 never-configured subscription, then destination-generation and future-admission settings win under locks; an already admitted send remains disclosed and its receipt retained.
- **NOTICE-09**: Given an uncertain save/resend followed by later settings changes, another actor or attempt-history compaction, then exact actor-bound receipt lookup/replay preserves the original result separately from current state; absent proof stays unknown.
- **NOTICE-10**: Given password login, Google completion/cancellation, pending account, expired return selection or denied browser storage, then only a successful authenticated flow restores one validated same-origin exact selection; no credentials/mutation payload or arbitrary redirect is retained.
- **NOTICE-08**: Given history compaction, fairness rotation or restart, when the same old accepted/unknown generation reappears, then dedupe remains and other subscriptions progress within the same bounded budget.

Development adds owner-reuse/API tests, PostgreSQL barriers, refusal/timeout/lost-commit lease cases, migration upgrade/downgrade, count and actual rendered-text limits, fair cursor wrap and stale-link/focus/login restoration UI assertions. Preserve legacy notification tests. Run backend initialization, typed API generation, relevant backend/PostgreSQL/UI checks, `just lint` and `just check`. Baseline is the same fixture with decision subscriptions disabled: zero decision-specific notices; enabling one matching subscription admits one selected generation. No numerical speed or delivery-latency claim is made.

#### Non-goals

- **Scope Excluded**: Telegram inbound approval/reply commands, bulk approval, automatic resume, per-chat recipient authentication, new per-project ACLs, new transport providers, Jules work and SDK machine approvals.
- **Scope Excluded**: enqueueing in owner mutation transactions, guaranteed notification of every transient event, automatic resend of uncertain sends, health dashboards, monitoring, production verification and CI changes.

#### Future write coordination

Owner behavior remains unchanged except the minimal exact discovery lookup. Auth semantics stay unchanged; exact return selection is an auth-UI navigation seam only. Production writes stay in notifications-owned modules, one shared maintenance call site/new helper, one additive migration, notification settings UI, exact inbox URL-selection seam, the exact discovery query/API/test paths and Google/password sign-in UI return hooks/helper/tests. Generated API output should change only notification and pipeline-run type resources plus any index output actually generated; list the latter before handoff. No MCP or Work Plan feature files, session store or logout cleanup are needed. Shared steering/architecture and migration head ordering require Host integration sequencing; future scope overlap alone does not serialize this Planning turn. No new feature dependency edge may be added without updating the repository's actual architecture declaration if its enforcing check requires one.

### 4. Lifecycle & Retirement Criteria

High Planning compares A/B/C with required Scout and Challenger; separate UX review is user-authorized on the drafted screens. High Development remains appropriate for persisted delivery evidence, migration and external-effect uncertainty. The subscription defaults, trusted-global-destination model and explicit uncertain resend are recommended assumptions within the requested scope, not completed authority. Host presents them and all remaining review findings at plan-accept. This turn does not accept, hand off, implement or test the product. `target-docs.md` carries the final proposed contract/screen ledger; retiring this proposal requires the ordinary accepted handoff.

