---
id: UC-configure-operator-notifications
title: Configure operator notifications
summary: "An operator saves a Telegram destination and verifies its delivery result before relying on it for severity-filtered notices. Channel setup grants no authority over runs or provider accounts."
area: notifications
primary_actor: Operator
supporting_actors:
  - Telegram
status: active
capabilities:
  - CAP-NOTIFY-operator-notifications
entrypoints:
  - modules/hub/app/features/notifications/decision_api.py
---

# [UC-configure-operator-notifications] Configure operator notifications

## 1. Goal

- **Goal**: Establish a tested destination for notices that need the operator's
  attention.
- **Scope**: Auto Hub notification-channel configuration and explicit delivery test.
- **Trigger**: The operator adds a Telegram destination.
- **Preconditions**: The operator has a signed-in Hub session and has obtained a bot
  token and chat identity from Telegram. Obtaining those credentials is external
  setup; Hub checks transport acceptance through the explicit test.

## 2. Main Success Scenario

1. The operator submits a destination and minimum notice severity
   (`CAP-NOTIFY-operator-notifications`). Screen: `UX-notifications`, `UX-notification-editor`.
2. Hub seals its token and returns the persisted channel without credentials
   (`CAP-NOTIFY-operator-notifications`). Screen: `UX-notification-editor`, `UX-notifications`.
3. The operator asks Hub to test the saved destination
   (`CAP-NOTIFY-operator-notifications`). Screen: `UX-notifications`.
4. Hub sends the test, records the accepted delivery and returns its result
   (`CAP-NOTIFY-operator-notifications`). Screen: `UX-notifications`.

5. The operator selects the channel's Decision subscription projects, kinds, timing and Hub origin (`CAP-NOTIFY-operator-notifications`). Screen: `UX-notifications`, `UX-decision-subscription`.
6. The operator reviews the trusted destination and effective gates, then saves the subscription (`CAP-NOTIFY-operator-notifications`). Screen: `UX-decision-subscription`, `UX-notifications`.

The channel test remains available independently; saving a Decision subscription does not require live Telegram acceptance.

## 3. Extensions

- **1a.** Duplicate name: Hub returns HTTP 409 without creating another channel;
  the operator chooses another name and resumes at step 1. Screen: `UX-notification-editor`.
- **1b.** Invalid channel settings: Hub returns HTTP 422 without persisting the
  invalid request; the operator corrects the settings and resumes at step 1. Screen: `UX-notification-editor`.
- **3a.** The saved channel no longer exists: Hub returns HTTP 404; the use case
  ends without sending a test. Screen: `UX-notifications`.
- **4a.** Telegram refuses delivery or the destination cannot be used: Hub returns
  `delivered=false` with the available failure detail and records the channel
  error. The operator can repair the channel and resume at step 3; successful
  configuration remains unverified until the test succeeds. Screen: `UX-notifications`, `UX-notification-editor`.

- **5a.** Invalid or deleted project selection is refused; the operator corrects settings and resumes at step5. Screen: `UX-decision-subscription`.
- **6a.** Stale subscription revision is refused; retained edits await explicit refreshed review before a fresh save. Screen: `UX-decision-subscription`.
- **6b.** The save response is uncertain; retain the exact request and Check save outcome or Retry same save. Current settings alone do not settle the request. An acknowledged save with failed refresh remains acknowledged. Screen: `UX-decision-subscription`.
- **6c.** Destination generation changed; the subscription is disabled and old-generation save is refused, including revision zero. The operator reviews the destination and resumes at step5. Screen: `UX-decision-subscription`.

## 4. Postconditions

- **Success guarantee**: The channel has token-free readback and a recorded
  successful test; enabled/severity settings govern subsequent broadcasts.
- **Minimal guarantee**: Invalid or duplicate creation does not create a second
  channel. A failed test remains a failed delivery result and cannot approve,
  resume or cancel development work.

## 5. Acceptance Criteria (Given / When / Then)

The scenarios exercise secret omission, unique names, schema validation, explicit
testing and delivery outcomes from `CAP-NOTIFY-operator-notifications`.

### Scenario: Save and test an enabled destination

- **Covers**: main success scenario.
- **Given**: A new destination with valid channel settings and a Telegram response
  accepting delivery.
- **When**: The operator creates the channel and requests a test.
- **Then**: Hub returns no token, reports `delivered=true`, records `last_sent_at`
  and clears `last_error`.
- **Test**: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.

### Scenario: Test a disabled, severity-filtered destination

- **Covers**: main success scenario, explicit-test boundary.
- **Given**: A channel is disabled or accepts only errors.
- **When**: The operator requests its explicit test.
- **Then**: Hub attempts the named channel despite broadcast filtering.
- **Test**: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.

### Scenario: Refuse a duplicate channel

- **Covers**: 1a.
- **Given**: A channel already uses the submitted name.
- **When**: The operator creates another channel with that name.
- **Then**: Hub returns HTTP 409 and leaves the original channel intact.
- **Test**: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.

### Scenario: Reject an invalid severity

- **Covers**: 1b.
- **Given**: The request contains a severity outside the supported literal values.
- **When**: The operator submits it.
- **Then**: Schema validation returns HTTP 422 before channel creation.
- **Evidence**: `modules/hub/app/features/notifications/schemas.py`; source inspection,
  no dedicated execution claimed.

### Scenario: Test a deleted destination

- **Covers**: 3a.
- **Given**: The saved channel was deleted.
- **When**: The operator tests its old identity.
- **Then**: Hub returns HTTP 404 and sends no notice.
- **Test**: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.

### Scenario: Retain a refused transport result

- **Covers**: 4a.
- **Given**: Telegram refuses a test because the chat is unavailable.
- **When**: The operator tests the channel.
- **Then**: Hub reports `delivered=false`, retains the error and does not set a
  successful-send timestamp.
- **Test**: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.

The named tests were inspected and mock Telegram transport. They do not establish
live bot access or receipt by the operator, and this use case records no new run.

### Scenario: Correct a refused subscription

- **Covers**: 5a, 6a, 6c.
- **Given**: Invalid project settings or stale revision/destination evidence.
- **When**: The operator saves the reviewed subscription.
- **Then**: No stale command is admitted; the operator explicitly corrects or refreshes the basis and uses a fresh request.
- **Test**: `modules/hub/tests/integration/features/notifications/test_decision_notices.py`; `modules/hub-ui/src/lib/features/configuration/notifications/decision-notices.integration.test.ts`.

### Scenario: Recover the original save independently of current state

- **Covers**: 6b.
- **Given**: A save response was lost and another operator changed current settings.
- **When**: The original actor checks or identically retries the original request.
- **Then**: Original receipt and current settings appear separately; missing proof stays unknown and changed input stays blocked until definite refusal or acknowledgement.
- **Test**: `modules/hub/tests/integration/features/notifications/test_decision_notices.py`; `modules/hub-ui/src/lib/features/configuration/notifications/decision-notices.integration.test.ts`.
