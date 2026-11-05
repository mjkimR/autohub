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
   (`CAP-NOTIFY-operator-notifications`).
2. Hub seals its token and returns the persisted channel without credentials
   (`CAP-NOTIFY-operator-notifications`).
3. The operator asks Hub to test the saved destination
   (`CAP-NOTIFY-operator-notifications`).
4. Hub sends the test, records the accepted delivery and returns its result
   (`CAP-NOTIFY-operator-notifications`).

## 3. Extensions

- **1a.** Duplicate name: Hub returns HTTP 409 without creating another channel;
  the operator chooses another name and resumes at step 1.
- **1b.** Invalid channel settings: Hub returns HTTP 422 without persisting the
  invalid request; the operator corrects the settings and resumes at step 1.
- **3a.** The saved channel no longer exists: Hub returns HTTP 404; the use case
  ends without sending a test.
- **4a.** Telegram refuses delivery or the destination cannot be used: Hub returns
  `delivered=false` with the available failure detail and records the channel
  error. The operator can repair the channel and resume at step 3; successful
  configuration remains unverified until the test succeeds.

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
