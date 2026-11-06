---
id: UC-access-hub
title: Access Hub with a human browser session
summary: "An operator signs in to Hub and uses a renewable browser session. Account and credential refusals preserve the separation between human access and machine automation."
area: access
primary_actor: Operator
supporting_actors: []
status: active
capabilities:
  - CAP-ACCESS-authentication-authorization
entrypoints:
  - modules/hub-ui/src/lib/features/auth/login/GoogleLogin.svelte
  - modules/hub-ui/src/lib/features/auth/login/LoginView.svelte
---

# [UC-access-hub] Access Hub with a human browser session

## 1. Goal

- **Goal**: access the management console with a renewable human session.
- **Scope**: Hub browser authentication and protected human REST operations.
- **Trigger**: the operator submits browser sign-in credentials.
- **Preconditions**: the Hub service and its configured account store are available.

## 2. Main Success Scenario

1. The operator submits their credentials (`CAP-ACCESS-authentication-authorization`,
   `UX-sign-in`).
2. Hub validates the account and establishes a browser session
   (`CAP-ACCESS-authentication-authorization`, `UX-sign-in`, `UX-app-shell`).
3. The UI keeps the access token in memory and accesses the protected management
   operation (`CAP-ACCESS-authentication-authorization`, `UX-app-shell`).
4. The browser renews its session using the server-owned refresh cookie when
   needed (`CAP-ACCESS-authentication-authorization`). Off screen: renewal is an
   automatic API exchange with no separate control or completion message.
5. The operator signs out and Hub revokes the browser session
   (`CAP-ACCESS-authentication-authorization`, `UX-app-shell`, `UX-sign-in`).

An optional exact notice entry follows `UC-receive-decision-notice`. Password sign-in preserves the requested query. Before Google departure, the UI retains only a validated key/fingerprint and timestamp for thirty minutes in tab sessionStorage. Approved completion consumes it once and navigates only to same-origin `/decisions`. Authentication policy and owner action authority stay unchanged.

## 3. Extensions

- **2a.** Invalid credentials: Hub refuses password sign-in; no authenticated
  session is established and the use case ends (`UX-sign-in`).
- **2b.** Caller lockout: the configured failed-login limit has been reached;
  Hub returns HTTP `429` with `Retry-After`, sends a masked operator notice and
  the use case ends until the caller may retry (`UX-sign-in`).
- **3a.** Account access withdrawn: the account is inactive or no longer approved;
  Hub refuses protected access with HTTP `401` and the use case ends (`UX-sign-in`).
- **4a.** Renewal unavailable: the cookie session cannot be renewed; the UI signs
  out that session generation and the use case ends (`UX-sign-in`).
- **4b.** Session changed during renewal: a response belongs to an older session
  generation; the UI discards it and resumes at step 3 for the current session.
  Off screen: generation fencing discards a response without changing the visible interface.

## 4. Postconditions

- **Success guarantee**: the operator accessed the protected operation and the
  explicitly closed browser session can no longer renew.
- **Minimal guarantee**: refused credentials do not grant protected human access;
  an obsolete renewal does not restore a closed session or replace a newer one.

## 5. Acceptance Criteria (Given / When / Then)

Rules exercised: human REST admission, browser refresh isolation/logout, frontend
session generation, caller lockout and current-account checks in
`CAP-ACCESS-authentication-authorization`.

### Scenario: Establish and close a browser session

- **Covers**: main success scenario.
- **Given**: an active approved operator with valid credentials.
- **When**: they sign in, renew and explicitly sign out.
- **Then**: protected access succeeds before sign-out, the login body contains no
  refresh token, and subsequent cookie renewal returns HTTP `401`.

### Scenario: Refuse an incorrect password

- **Covers**: 2a.
- **Given**: an unlocked caller and an existing operator account.
- **When**: the caller supplies an incorrect password.
- **Then**: password sign-in is refused and no usable human session is granted.

### Scenario: Respect the caller lockout

- **Covers**: 2b.
- **Given**: the caller has reached the configured failed-login threshold.
- **When**: they retry before the lockout expires.
- **Then**: Hub returns HTTP `429` with a retry delay and the notification omits
  the complete caller address.

### Scenario: Refuse a withdrawn account

- **Covers**: 3a.
- **Given**: an access token issued before the account became inactive or pending.
- **When**: it is used for a protected Hub operation.
- **Then**: Hub returns HTTP `401`.

### Scenario: End a session that cannot renew

- **Covers**: 4a.
- **Given**: an expired access token and an unusable browser refresh session.
- **When**: the UI attempts renewal.
- **Then**: the current UI session is signed out rather than repeatedly retrying.

### Scenario: Ignore an obsolete renewal

- **Covers**: 4b.
- **Given**: a renewal began before logout or a newer sign-in.
- **When**: its response arrives afterward.
- **Then**: it cannot restore the closed session or overwrite the newer token.

## 6. Evidence

Inspected checks: `modules/hub/tests/integration/auth/test_auth_api.py`,
`modules/hub/tests/unit/common/test_auth_throttle.py`,
`modules/hub-ui/src/lib/api/client.test.ts` and
`modules/hub-ui/src/lib/stores/session.test.ts`. Scenarios describe the inspected
contract, not a new recorded execution or live identity-provider verification.

### Scenario: Recover exact notice navigation after admission

- **Covers**: optional notice entry.
- **Given**: A valid exact notice link and successful approved sign-in.
- **When**: Password or Google admission completes.
- **Then**: The exact identity reaches authenticated Decisions; expired/malformed/denied storage offers conditional reopen guidance, and cancellation or pending/rejected exchange opens no owner review.
- **Test**: `modules/hub-ui/src/lib/features/auth/login/notice-return.integration.test.ts`, `GoogleLogin.integration.test.ts` and `LoginView.integration.test.ts` in the same directory. Controlled admission responses; no live OAuth claim.
