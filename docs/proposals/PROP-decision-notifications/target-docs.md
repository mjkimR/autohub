---
id: PROP-decision-notifications-target
title: Living Spec targets for decision notifications
summary: "Proposed decision subscription, transport outcome and exact owner-link contracts with notification and inbox screen drafts."
status: draft
proposal: PROP-decision-notifications
created_at: 2026-11-06
targets:
  - file: docs/capabilities/notifications/CAP-NOTIFY-operator-notifications.md
  - file: docs/usecases/notifications/UC-configure-operator-notifications.md
  - file: docs/usecases/notifications/UC-receive-decision-notice.md
  - file: docs/usecases/delivery/UC-resolve-run-question.md
  - file: docs/usecases/sdd/UC-decide-sdd-proposal.md
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
  - file: docs/ux/settings/UX-notifications.md
  - file: docs/ux/settings/UX-decision-subscription.md
  - file: docs/ux/settings/UX-decision-notice-history.md
  - file: docs/ux/delivery/UX-decision-inbox.md
  - file: docs/steering/ux-objects.md
  - file: docs/steering/glossary.md
  - file: docs/architecture/ARCH-06-execution.md
---

# [Blueprint] Decision notifications

## 1. Capability and decision plan

Extend `CAP-NOTIFY-operator-notifications` with opt-in channel-owned Decision subscriptions, severity/project/kind composition, bounded discovery and digest construction, immutable message membership, per-generation deduplication and accepted/refused/unknown transport evidence. Narrow its existing durable-queue exclusion to retain the legacy generic notice behavior while allowing only these decision-specific receipts. `PADR-decision-notice-delivery` is the proposed cross-feature decision. Owner mutation/approval contracts remain unchanged.

`ARCH-06-execution` places bounded fair notification work inside shared maintenance and isolates transport failures from existing execution work. The notification feature reads existing owner discovery and adds no evaluator/controller. Add Decision subscription to the glossary as opt-in project/kind/delivery settings for one global Notification channel; it excludes the owner decision and authenticated identity of Telegram chat participants.

## 2. Use case changes

Extend `UC-configure-operator-notifications` after its existing channel save/test steps:

5. The operator opens Decision notices for a channel and selects project scope, kinds, immediate or 15-minute digest, and the Hub origin. Screen: UX-decision-subscription.
6. The operator reviews effective channel severity/enablement and trusted-destination disclosure, then saves the subscription. Screen: UX-decision-subscription; parent `UX-notifications` shows the persisted summary.

Add extensions 5a unavailable/deleted project, 6a stale revision, 6b unknown save response, and 6c destination change requiring review/re-enable. Invalid/stale requests preserve editable settings and never silently adopt new revisions. An uncertain save retains request UUID/payload in the open editor; Check saved settings reads current data, and Retry same save reuses the original command. Acknowledged save plus refresh failure stays acknowledged with a Refresh failed disclosure. Saving does not require a live Telegram test.

Add UC-receive-decision-notice, with capabilities `CAP-NOTIFY-operator-notifications`, `CAP-PR-operator-decisions`, `CAP-SDD-native-delivery` and `CAP-SDD-workflow-control` as applicable. Reciprocal capability usecase links are required when creating this use case.

1. The operator receives a minimal observed decision notice at the trusted destination and follows its exact review link. Screen: `UX-decision-inbox` after existing `UX-sign-in` if required.
2. Hub authenticates, validates the selection and performs exact owner review, with the native inspection/CAS effects already owned by existing decision capabilities. Screen: `UX-decision-inbox`.
3. The operator sees the selected owner review and chooses an explicit permitted next action under its existing use case. Screens: `UX-run-decisions`, `UX-sdd-workflow-request`, `UX-sdd-run` as appropriate; their controls and authority remain unchanged.
4. The operator can inspect notice delivery evidence separately and explicitly review a failed/unknown resend. Screen: UX-decision-notice-history.

Extensions: 1a malformed link ends with Open inbox; 2a changed/resolved/inaccessible subject offers Refresh inbox without substituting another subject; 2b inspection read error offers Retry review or Open inbox; 4a unknown transport warns that Send again may duplicate; 4b superseded generation has no resend and offers Open inbox; 4c stale delivery/subscription revision requires refreshed explicit review. The success guarantee is exact owner navigation and visible transport evidence, not reading or applying a decision. Notification failure changes no owner state.

Add the optional notice-link entry to step1 of `UC-resolve-run-question` and `UC-decide-sdd-proposal`, and relevant request/integration steps of `UC-complete-sdd-workflow`. Keep their current approval subjects, unknown-outcome recovery and owner dialog contracts unchanged.

## 3. Screens

### Contrasting candidates

- **A: separate subscription and delivery-history dialogs under each channel card, recommended**. The subscription form focuses on future notices; history focuses on transport evidence and explicit resend. Exact owner controls remain in Decisions.
- **B: add settings and all delivery history inline to Notifications**. Avoids dialogs but competes with channel setup/testing and grows each card into a work queue.
- **C: make Decisions own channel subscriptions**. Places discovery near delivery settings but introduces destination/credential concerns into a decision surface.

Recommend A. Use existing layout tokens/components. These drafts define content and states, not a new visual system. User requested separate UX review before code.

### UX-notifications — Notification channels (screen draft extension)

**Use cases**: `UC-configure-operator-notifications`, UC-receive-decision-notice. **Capability**: `CAP-NOTIFY-operator-notifications`.

#### Purpose

Maintain trusted destinations and see whether decision notices are effectively enabled. Channel cards remain primary; secondary settings/history open dedicated dialogs.

#### Content

- Notification channel: retain existing name, chat, severity, enabled state, Send test/Edit/Enable/Delete.
- Decision subscription summary below channel facts: Off by default; selected-project count or All current and future projects; kind selection; immediate or 15-minute digest; last loaded time.
- Effective delivery: Channel disabled or Severity excludes warning if those gates block the enabled subscription. Credential/chat changes show Review destination before re-enabling.
- Decision notices: opens subscription dialog.
- Notice history: opens history dialog with accepted/failed/unknown count from bounded current read, not a claim about every historical record.

#### States

Retain existing populated/empty/loading/testing/error behavior. Cards without subscriptions show Off and Decision notices. Refresh failure preserves prior acknowledged settings with an observation timestamp and retry. Channel deletion removes notice settings/evidence; existing delete confirmation says so. An admitted send may finish after disabling/deleting; disclose this with the relevant action.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Decision notices | `UC-configure-operator-notifications` 5 | populated | populated | UX-decision-subscription | `CAP-NOTIFY-operator-notifications` | Opens current subscription and channel gates. |
| Notice history | UC-receive-decision-notice 4 | populated | populated | UX-decision-notice-history | `CAP-NOTIFY-operator-notifications` | Loads bounded outcome records. |
| Existing channel actions | global: retain current channel maintenance | populated | populated | `UX-notification-editor` | `CAP-NOTIFY-operator-notifications` | Existing test/save feedback remains unchanged. |
| Navigate to Decisions | global: inspect pending work separately | populated | populated | `UX-decision-inbox` | | Opens owner discovery without changing notices. |

### UX-decision-subscription — Decision notice settings (modal draft)

**Use case**: `UC-configure-operator-notifications`. **Capability**: `CAP-NOTIFY-operator-notifications`.

#### Purpose

Save which observed decisions this trusted channel may disclose and when. Facts to commit: destination/chat and origin, project scope including future-project meaning, kind filters, effective channel gates, delivery mode and in-flight limit. Delivery history belongs in its sibling dialog.

#### Content

The settings form is primary above its disclosure and Save/Cancel controls.

- Notification channel: read-only name/chat, enabled flag and minimum severity.
- Decision subscription: enabled toggle (initial off); selected projects chooser or explicit All current and future projects; six decision-kind choices; immediate or 15-minute digest; Hub origin field and constructed example link.
- Effective outcome: current disabled/severity blocker, observed-not-live wording, existing matching pending decisions become eligible on enable/filter expansion, and a 10-entry/3,500-character batch cap.
- Trust confirmation when enabling or changing destination/scope: The chat is trusted for selected project names, run/PR identities and decision metadata. Participants still need Hub sign-in to review. No question/answer content is sent.
- Future-admission disclosure: stopping or changing notices cannot recall an admitted external message.
- Save status: saved revision/time; unknown save request ID and Check saved settings / Retry same save when applicable.

#### States

- **loading**: wait for settings, Cancel remains available; Save disabled.
- **populated**: edit settings, review disclosure, Save or Cancel.
- **saving**: lock mutation controls for this request; retain immutable UUID/payload until acknowledgement.
- **conflict**: retain edits and show changed revision; Refresh for review clears confirmation before fresh save.
- **unknown**: retain original request and disable changed-input save; Check saved settings or Retry same save; Close preserves unresolved intent in the active settings session. A full reload cannot claim recovery of an unacknowledged local payload; read saved settings before a new reviewed command.
- **error**: validation refusal identifies correction without implying transport delivery; Cancel or correct/review/save.
- **saved-refresh-error**: acknowledged save stays visible with Refresh failed; no replacement save is substituted.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Change project/kind/destination scope | `UC-configure-operator-notifications` 5 | populated | populated | | `CAP-NOTIFY-operator-notifications` | Effective summary updates; prior trust confirmation clears. |
| Save reviewed subscription | `UC-configure-operator-notifications` 6 | populated | saving | `UX-notifications` | `CAP-NOTIFY-operator-notifications` | Acknowledged settings and revision appear; failure retains form. |
| Refresh for review | `UC-configure-operator-notifications` 6a | conflict | populated | | `CAP-NOTIFY-operator-notifications` | Shows current settings and clears old confirmation. |
| Check saved settings / Retry same save | `UC-configure-operator-notifications` 6b | unknown | unknown, populated | | `CAP-NOTIFY-operator-notifications` | Reads current settings or replays exact original command; read alone does not prove an absent request failed. |
| Review changed destination | `UC-configure-operator-notifications` 6c | populated | populated | | `CAP-NOTIFY-operator-notifications` | Reveals current chat/origin and requires fresh trust confirmation. |
| Cancel or close | global: return without another save | populated, unknown, error | populated | close | | Parent remains; unresolved session intent is retained. |

### UX-decision-notice-history — Decision notice delivery history (modal draft)

**Use case**: UC-receive-decision-notice. **Capability**: `CAP-NOTIFY-operator-notifications`.

#### Purpose

Inspect whether a particular notice was accepted, refused or remains unknown, and explicitly review any resend. Owner decision progress is a separate exact link.

#### Content

A bounded newest-first attempt list is primary, with filters/channel context above and cursor navigation below.

- Notification channel: name/chat and destination generation; last-loaded timestamp.
- Operator notice: kind/project/run references, generation and observation time; admitted/delivered/failed/unknown times and safe failure code; no question/answer body.
- State detail: Accepted by Telegram is not read/applied; Unknown may already have been delivered; superseded/owner-unavailable records are inspect-only.
- Open exact review link when a retained subject remains available; Open inbox for unavailable/superseded evidence.
- Send again review: current destination/filter context, explicit May duplicate acknowledgement for unknown, and Confirm send again/Cancel. Both definite failures and unknowns retain original history and create at most one attempt per request UUID.
- History compaction: older detailed attempts may be summarized; retained generation state still prevents duplicate admission.

#### States

- **loading**: wait with Close available; resend disabled.
- **populated**: inspect/read; refresh or page; review an eligible failed/unknown notice.
- **empty**: No decision notice history; Close or open settings.
- **error**: keep prior observations and time, offer Refresh; mutation controls unavailable until current basis loads.
- **reviewing-resend**: show current basis and duplicate warning where needed; Cancel or Confirm.
- **sending**: lock resend controls; preserve the request intent.
- **unknown-resend**: show request ID, Check outcome and Retry same resend command; no changed-payload request. Closing/reopening retains active session intent; full reload recovers only durable history and explicitly labels unavailable unacknowledged intent.
- **changed**: subscription or generation changed; no send, Refresh for review or Open inbox.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open exact review | UC-receive-decision-notice 1 | populated | loading | `UX-decision-inbox` | `CAP-NOTIFY-operator-notifications` | Exact link authenticates and inspects its owner; no authority is embedded. |
| Review Send again | UC-receive-decision-notice 4 | populated | reviewing-resend | | `CAP-NOTIFY-operator-notifications` | Current destination/generation and possible duplicate are disclosed. |
| Confirm send again | UC-receive-decision-notice 4, UC-receive-decision-notice 4a | reviewing-resend | sending | | `CAP-NOTIFY-operator-notifications` | One durable resend attempt is admitted; receipt shown independently of owner progress. |
| Refresh / page | global: browse bounded transport evidence | populated, error | loading | | | Current page and time reload; no send occurs. |
| Changed/superseded evidence | UC-receive-decision-notice 4b, UC-receive-decision-notice 4c | changed | populated | `UX-decision-inbox` | | Open inbox offers fresh review; no replacement generation is silently selected. |
| Check outcome / Retry same resend | UC-receive-decision-notice 4a | unknown-resend | unknown-resend, populated | | `CAP-NOTIFY-operator-notifications` | Reads retained command evidence or replays its identical UUID/payload. |
| Cancel review / Close | global: leave without another attempt | reviewing-resend, populated, unknown-resend, empty, error | populated | close | | Parent remains; uncertain session intent is not silently replaced. |

### UX-decision-inbox — Exact notice link landing (screen draft extension)

**Use cases**: UC-receive-decision-notice, `UC-resolve-run-question`, `UC-decide-sdd-proposal`, `UC-complete-sdd-workflow`. **Capabilities**: existing inbox owners plus `CAP-NOTIFY-operator-notifications` for notice origin only.

#### Purpose and content

Keep the current filtered worklist primary. An exact link adds a visible landing-status region while authenticated owner review runs, independent of list pagination/filter state. Show key/kind provenance and observed basis without question text before owner authorization. Sign-in happens through existing `UX-sign-in` rendered in place; retain the original encoded query. After exact success, the existing owner dialog is the primary decision surface. The link does not save answers, grant approval or resume work.

#### States

Keep existing states; add **link-reviewing** with inspection status and Open inbox; **link-changed** for missing/replaced/inaccessible evidence with Refresh inbox; **link-error** with Retry review/Open inbox; **link-invalid** with no request and Open inbox. Automatic initial link review runs once per exact URL identity; rerendering or owner-dialog dismissal does not loop inspection. Failed/dismissed inspection requires explicit Retry review. Ordinary/native head/generation changes never select another subject automatically.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Follow authenticated notice link | UC-receive-decision-notice 1, UC-receive-decision-notice 2 | populated | link-reviewing | | `CAP-PR-operator-decisions` | Exact review identity loads even outside the first page. |
| Exact owner review succeeds | UC-receive-decision-notice 3 | link-reviewing | reviewing | `UX-run-decisions` | `CAP-PR-operator-decisions` | Only the selected question/request opens with existing native panels as appropriate. |
| Retry review | UC-receive-decision-notice 2b | link-error | link-reviewing | | `CAP-PR-operator-decisions` | Repeats exact authenticated inspection, not a decision mutation. |
| Open/Refresh inbox | UC-receive-decision-notice 1a, UC-receive-decision-notice 2a | link-invalid, link-changed, link-error | loading | | | Clears obsolete selection and shows current discovery without automatically opening a replacement. |
| Close owner review / leave Decisions | global: return from exact inspection | reviewing, populated | populated | close | | Keeps ordinary list context and restores focus to landing action when no originating row exists. |

## 4. Object register additions

| Object | Role | Representations | Calls to action |
| --- | --- | --- | --- |
| Notification channel | Operator | Decision notice effective-gate summary and trusted destination context | Open Decision notices, inspect Notice history |
| Decision subscription | Operator | Project/kind selection, immediate/digest preference, revision and trust disclosure | Review/save settings, enable/disable, check saved settings, retry same save |
| Operator notice | Operator | Exact observed subject links, immutable admitted membership, accepted/failed/unknown attempt history | Inspect delivery, open exact review, review Send again, check outcome, retry same resend |
| PR run / Run question / Native SDD activity | Operator | Exact authenticated notice-link landing status | Review exact owner, refresh inbox |

## 5. Future file coordination and evidence

New notification files are expected under the existing notifications parent: `decision_models.py`, `decision_schemas.py`, `decision_repo.py`, `decision_service.py`, `decision_usecase.py` and `decision_delivery.py`; the final task decomposition settles their names. Existing exact seam edits are `notifications/api/v1.py`, `notifications/models.py`, `notifications/services.py`, `notifications/telegram.py`, maintenance `task.py`, notifications UI `NotificationsView.svelte` and its state helper, plus `DecisionInbox.svelte` and its adjacent tests. New maintenance helper and tests remain notification-specific.

One new migration must use the landed latest head at implementation/integration; do not edit sibling Work Plan migration files or generated type resources. Shared generated index output, steering rows and `ARCH-06-execution` require Host sequencing if changed by another unit. No write to MCP or Work Plan feature owners is planned. Baseline and enforcement examples are in the proposal, and source inspection is retained in `materials/owner-seams.md`.
