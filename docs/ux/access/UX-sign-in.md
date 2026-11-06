---
id: UX-sign-in
title: Sign-in screen
summary: "Authenticate a human browser session with a password or configured Google sign-in and show recoverable admission outcomes."
area: access
element: screen
status: active
usecases:
  - UC-receive-decision-notice
  - UC-access-hub
capabilities:
  - CAP-ACCESS-authentication-authorization
---

# [UX-sign-in] Sign-in screen

## 1. Purpose

- **Primary task**: establish a Browser session.
- **Facts to commit**: the remembered email, a password entered for this attempt and any sign-in refusal. Google sign-in is offered only when enabled.
- **Secondary items**: theme preference stays beside the sign-in surface; the authenticated console is `UX-app-shell`.

## 2. Content

The credential form is the primary region. Provider sign-in and admission messages appear above it. The root layout substitutes this screen for protected content at the requested URL; it does not require a separate login route.

- Browser session (credential form): email and password, with a submitting button state.
- Browser session (Google admission): Continue with Google, completion progress and pending/rejected/suspended or existing-account messages when returned.
- Browser session (restoration): the layout first displays Restoring session before deciding between this screen and `UX-app-shell`.
- Theme preference (toggle): available without signing in.

## 3. States

- **populated**: the form accepts credentials; the operator can sign in or choose enabled Google sign-in.
- **submitting**: email, password and submit controls are disabled while password admission is pending.
- **google-completing**: Google exchange shows progress; a successful approved exchange opens the console.
- **error**: missing credentials, password refusal, caller lockout or network failure leaves a retryable form and a message.
- **session-ended**: logout or unavailable renewal returns to this form; no account-withdrawal explanation is added by the layout itself.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Submit Sign in | `UC-access-hub` 1 | populated | submitting |  | `CAP-ACCESS-authentication-authorization` | Signing in is shown; the password is cleared on success. |
| Receive successful admission | `UC-access-hub` 2 | submitting | populated | `UX-app-shell` | `CAP-ACCESS-authentication-authorization` | Signed in toast and the protected console appear. |
| Receive credential refusal or lockout | `UC-access-hub` 2a, `UC-access-hub` 2b | submitting | error |  | `CAP-ACCESS-authentication-authorization` | Inline refusal or retry-delay guidance and a toast remain visible. |
| Return after access or renewal ends | `UC-access-hub` 3a, `UC-access-hub` 4a, `UC-access-hub` 5 | session-ended | populated |  | `CAP-ACCESS-authentication-authorization` | The credential form replaces authenticated content. |
| Continue with Google | global: optional provider admission alongside the modeled password sign-in | populated | google-completing | end | `CAP-ACCESS-authentication-authorization` | The browser navigates to provider authorization; callback results return here. |
| Toggle theme | global: a visual preference independent of authentication | populated | populated |  |  | The selected theme changes. |
| Complete approved notice sign-in | `UC-receive-decision-notice` 1b | submitting, google-completing | populated | `UX-decision-inbox` | `CAP-PR-operator-decisions` | Restores only validated exact identity; otherwise conditional reopen guidance appears. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/routes/+layout.svelte`, `modules/hub-ui/src/lib/features/auth/login/LoginView.svelte` and `modules/hub-ui/src/lib/features/auth/login/GoogleLogin.svelte`. Inspected checks: `modules/hub-ui/src/lib/features/auth/login/LoginView.integration.test.ts` and `modules/hub-ui/src/lib/features/auth/login/GoogleLogin.integration.test.ts`. These references do not record a browser or live identity-provider execution.

## 6. Exact notice return

The optional notice context contains only validated decision key/fingerprint and a thirty-minute tab-local timestamp. Password admission keeps the requested URL. Before Google departure, the helper retains that bounded identity; approved completion consumes it once and returns only to same-origin Decisions. No mutation payload, credential or arbitrary redirect is retained. Expired, malformed, missing or denied storage leaves successful login intact and displays: Signed in. If you arrived from a decision notice, reopen its original link to review the exact decision.
