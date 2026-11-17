---
id: OPS-operator-sign-in-refusals
title: "Operator sign-in and session refusal routing"
status: active
summary: "Routes an operator who cannot obtain or keep a Hub browser session via password or Google login to the configuration, account-approval or session owner by page message, Google return value and HTTP status; Google settings and platform logs stay outside Hub evidence."
related_capabilities:
  - CAP-ACCESS-authentication-authorization
related_usecases:
  - UC-access-hub
---

# [OPS-operator-sign-in-refusals] Operator sign-in and session refusal routing

An operator reports that they cannot sign in to Hub, or that a session that worked stops working. Google login can
complete at Google and still grant no Hub session, because Hub approval, account state and session generation are
separate checks; a password login can fail for lockout rather than a wrong password. The sign-in page message, the
`google` query value on return and the HTTP status of the refused request separate configuration faults from account
decisions.

## Routing

On return from Google, the sign-in page reads `google=complete` and calls `POST /api/v1/auth/google/exchange`, whose
`status` is `approved`, `pending`, `rejected` or `suspended`; any other `google` value is shown without an exchange.

| Symptom or state | Discriminating evidence | Next useful owner |
| --- | --- | --- |
| No Google button on the sign-in page | `GET /api/v1/auth/google/options` returns `enabled: false`, and `GET /api/v1/auth/google/start` returns HTTP `404` | [Google login](../runbooks/access.md#google-login) step 3; `CAP-ACCESS-authentication-authorization` §3 rules 4 and 13 |
| Google returns the browser to an HTTP error instead of the sign-in page | The callback answers HTTP `405` with an `Allow` header, because the configured response mode expects the other method | [Google login](../runbooks/access.md#google-login) step 4; `CAP-ACCESS-authentication-authorization` §4 callback row |
| "Google sign-in expired or failed. Please try again." | Return carried `google=complete`, but the exchange request failed: the short-lived callback cookie was missing or expired, or the request Origin differs from `GOOGLE_AUTH_FRONTEND_URL` | [Google login](../runbooks/access.md#google-login) steps 3–4 (same-origin callback and frontend, secure cookies); `CAP-ACCESS-authentication-authorization` §4 exchange row |
| "Google sign-in was cancelled or failed. Please try again." | Return carried a `google` value other than `complete` or `existing_account`; no exchange ran | Retry the login; if it repeats, the callback registration in [Google login](../runbooks/access.md#google-login) step 2 |
| "This email belongs to an existing account. Use its password login." | Return carried `google=existing_account`; Google identity is not linked to a local account by email | [Account administration](../runbooks/access.md#account-administration); `CAP-ACCESS-authentication-authorization` §4 Shared identity and account administration |
| "Your account is awaiting administrator approval." | Exchange `status` `pending`; the account appears as pending on **Account approval** (`/admin/users`) | A superadmin through [Account administration](../runbooks/access.md#account-administration); `CAP-ACCESS-authentication-authorization` §3 rule 3 |
| "Your access request was declined." or "Your account is suspended." | Exchange `status` `rejected` or `suspended`; the account's latest access events on **Account approval** name the action and reason | A superadmin through [Account administration](../runbooks/access.md#account-administration); `CAP-ACCESS-authentication-authorization` §4 account access actions |
| Password sign-in refused repeatedly, then a retry delay | HTTP `429` with `Retry-After`; operators receive a lockout notice with a masked caller address | `UC-access-hub` extension 2b; the threshold belongs to app-common per `CAP-ACCESS-authentication-authorization` §4 |
| A working session starts failing on protected calls | Protected REST calls return HTTP `401` after an access change to the account (suspend, reject, demote or reactivation), which advances its `auth_version` | `UC-access-hub` extension 3a; after reactivation, a fresh sign-in per [Account administration](../runbooks/access.md#account-administration) |
| The UI signs out without an explicit logout | Browser renewal through `POST /api/v1/auth/browser/refresh` failed, so the UI ended that session generation | `UC-access-hub` extension 4a; `CAP-ACCESS-authentication-authorization` §3 rules 5–6 |
| A superadmin's account action is refused | The action conflicts on a stale `expected_version`, or targets the acting administrator, the bootstrap account or the last active approved administrator | Reload and review per [Account administration](../runbooks/access.md#account-administration); `CAP-ACCESS-authentication-authorization` §4 account access actions |

If no Google path works and no superadmin can sign in, use the deployment's `FIRST_USER_EMAIL` password account named
in [Google login](../runbooks/access.md#google-login). For evidence that matches no row, take the HTTP status and
route to `CAP-ACCESS-authentication-authorization` §3 and §4.

## Normal-state observation

After the owner's action, a fresh sign-in returns an access token, sets the `autohub_refresh` cookie and
`GET /api/v1/users/me` returns the intended approved account; for Google, the exchange reports `status` `approved`.
`CAP-ACCESS-authentication-authorization` owns these facts. A deployment change is confirmed only by
[Live validation](../runbooks/access.md#live-validation), not by one successful sign-in.

## Authority boundary

Google owns the OAuth client, consent screen and the identity it asserts. The Cloud Run platform request log is outside
Hub's callback-query filtering, so Hub evidence cannot show what that log retained. Machine-key and MCP refusals are
routed by `OPS-mcp-client-connection-refusals`, not here.

## Update triggers

- `CAP-ACCESS-authentication-authorization` §3 rules 3–6 or 13, or the §4 Google, browser-session or account-action
  contract changes.
- The `google` return values, exchange statuses or messages in
  [GoogleLogin.svelte](../../modules/hub-ui/src/lib/features/auth/login/GoogleLogin.svelte) change.
- The pinned `app-prebuilt-auth` dependency in [pyproject.toml](../../modules/hub/pyproject.toml) changes its callback,
  exchange or account-action behavior.
