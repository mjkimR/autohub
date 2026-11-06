# Notification owner seam inspection

Inspected at `4db099a979619cf105a8be7a137fc12a67ff2496`. Scout performed read-only source inspection, with unchanged tree `d7fd910de502cda58c083df24f42b320b63d302f`; no product tests ran.

- `CAP-NOTIFY-operator-notifications`: global channels and nontransactional Telegram delivery, `modules/hub/app/features/notifications/models.py:12-30`, `notifier.py:36-106`; no subscription model exists.
- `CAP-PR-operator-decisions` and `ADR-decision-inbox-read-projection`: `pipeline_runs/models.py:207-225` and `discovery_projection.py:99-127` retain exact keys/fingerprints inside owner writes. `discovery_repo.py:8-35` offers indexed bounded keyset reads.
- Exact review: `pipeline_runs/usecases/discovery.py:38-53` checks subject and fingerprint; `:94-121` commits native inspection under the predecessor CAS. Background notification work must use discovery reads, never this inspection operation.
- `CAP-ACCESS-authentication-authorization`: `app/router.py:34-39` authenticates human REST; `projects/models.py:9-25` has no per-user project owner; discovery query has no per-user filter. Preserve global operator visibility and state the shared Telegram destination trust boundary.
- `UX-decision-inbox`: `DecisionInbox.svelte:33-86` has row Review but no URL selection; `routes/decisions/+page.svelte:1-5` simply mounts it. `routes/+layout.svelte` renders LoginView in place until the Browser session exists, so password sign-in retains query parameters. Challenger inspection identified that `GoogleLogin.svelte` leaves the app and exchanges a root callback without those parameters; bounded exact-selection return retention is therefore required for Google.
- `CAP-NOTIFY-operator-notifications`: `telegram.py` caps at4096characters and converts all request errors to TelegramError; structured accepted/refused/unknown evidence is needed for decision-specific sends without changing legacy notifier behavior.

High Planning incoming refs were inspected for `CAP-NOTIFY-operator-notifications`, `CAP-PR-operator-decisions` and their relevant ADRs. Principal consumers include `UC-configure-operator-notifications`, `UX-notifications`, `UX-notification-editor`, `UX-decision-inbox`, `ARCH-05-2-components`, `ARCH-06-execution`, `CAP-SDD-workflow-control` and `CAP-MCP-tool-access`. Only notification-owned contracts and the exact inbox landing reflection change; sibling MCP/WorkPlan behavior remains read-only.

The Scout did not audit every auth path, runtime tick cadence, deployment base-path setup or every native decision kind. Development must compare each kind against existing owner predicates and verify actual URL encoding/base-origin construction. No external Telegram contract or live observation is claimed.
