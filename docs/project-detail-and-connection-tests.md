# Project detail and AI catalog connection tests

Clicking a project name or **Open** navigates to the `/projects/{id}` detail page.
The Overview, Runs, Connections, Automation, and Settings tabs are distinguished by
the `?tab=...` URL, so bookmarks and the back button work. The all-projects runs
page is also kept.

| Tab | Role |
| --- | --- |
| Overview | Recent development runs, verification results per catalog, GitHub checks, auto-merge summary |
| Runs | Enroll, observe, and stop runs for the project, plus attempt history |
| Connections | GitHub settings, read-only access check, Codex/Jules setup guidance, catalog selection and real PR test |
| Automation | Auto-enroll, auto-fix, and auto-merge policies and the schedule entry point |
| Settings | Change name and active state, delete the project |

## Connection tests

The GitHub access check and the Codex PR test are separate. The access check posts
no comments and cannot verify Codex's OAuth connection or Cloud environment. Cloud
setup is done once in Codex web. No desktop app or local helper is required.

In **Test AI catalog**, select a Codex or Jules catalog and run **Start PR test**.
Results are per project × catalog and store the catalog ID, name, kind, and connector
at creation time. A successful connection does not guarantee readiness of other
repositories or catalogs. Existing Codex-only history is shown as Legacy Codex and
is not treated as verification of a new catalog.

Codex creates a dedicated branch and a Draft PR in the target repository and posts
a mention as the Hub's GitHub connector account. Changing the catalog does not change
the Codex account. The actual account is determined by the project's GitHub connector
and that account's Codex connection.
It asks Codex to replace the test file `.autohub/connection-tests/{id}.txt` with a
unique verification string and push to the same branch. After the file contents and
the new head SHA are confirmed, verification succeeds only when the configured CI
workflows and all required jobs on that head pass.
A comment or a mere head change alone does not count as success. Do not push to the
test branch directly, because the author of a manual push cannot be confirmed as Codex.

Jules checks the repository connection in the Sources API with the API connector
specified in the catalog. It sets the dedicated branch as the session's startingBranch
and runs with `AUTO_CREATE_PR`. After confirming that the PR created by Jules derives
from the test branch, it verifies the completed session's changes and CI. The PR base
must also be the dedicated test branch; if the PR targets the default branch, the test
fails and the ownership-confirmed PR is closed. The CI branch filter must allow PRs
targeting `autohub-connection-test/**`. A Draft is requested, but AutoHub's merge
exclusion still holds if the provider creates a regular PR.

Tests are kept in a separate `connection_tests` history. The development pipeline's
auto-fix and auto-merge policies do not apply. Test branches and recorded PRs are
rejected by regular run enrollment and are checked again right before merge. Even
before Jules's output PR number is discovered, they are blocked by head/base names,
test markers and labels, and ancestry from the test commit saved in advance. Ancestry
lookups are limited to tests whose remote work termination and output are not yet
confirmed, and while unconfirmed, the block stays even after 24 hours.
Ownership-confirmed PR numbers are preserved separately so they stay blocked after
cleanup finishes or the base changes, and completed past history does not add GitHub
lookups for every regular PR. Jules test sessions are not included in automatic PR
enrollment of regular task sessions. AutoHub does not merge these PRs even if the
Draft is lifted.
This does not block merges by external GitHub automation or people.

## Results and cleanup

| Result | Cleanup |
| --- | --- |
| Success | Close the PR and delete the dedicated branch on the next pass |
| Failure, timeout, cancellation | Close the PR and keep for at least 24 hours after termination. If Jules remote work or output is unconfirmed, keep cleanup and the merge block in place |
| Cleanup error | Keep the original verification result and retry cleanup only |

The test time limit is 1 hour from creation. If CI skips Draft PRs or the test file
path, the push may be confirmed but verification does not succeed, and the test ends
as unverifiable when the time limit passes. Hub cancellation does not guarantee that
Codex or Jules work already running stops.
For Jules, session output is still queried after cancellation to close late PRs.
Even if Jules authentication breaks, already confirmed PRs are closed on GitHub, and
recent PRs are searched regardless of target branch. Ownership is accepted only for a
PR returned by the Jules session or a PR with that test ID's marker, and only after
repository and ancestry are verified. Confirmed PRs get the
`<!-- autohub-connection-test:<test ID> -->` body marker and the
`autohub-connection-test` label. If labeling fails due to permissions, a warning is
logged, and protection and cleanup by the stored PR ID remain.

PRs that match only by ancestry go on a pending-confirmation list and are blocked from
merge only. Their body and labels are not edited, and they are not closed and their
branches are not deleted. This rule also applies to regular PRs branched after the test
commit was merged into main externally. Existing history without ownership evidence is
re-checked. Lookup failures or unconfirmed remote work are not treated as completed
cleanup. Cleanup resumes automatically after authentication is restored and remote work
termination and output are confirmed. GitHub authentication and access remain required
for cleanup. It is not guaranteed if external work recreates the branch after cleanup
completes.

When automatic confirmation is impossible, such as when only the creation intent was
saved and the actual request was never sent, a finished Jules test can be recovered
from **Review cleanup**. After checking the provider history, confirm that no remote
work exists or that it has fully ended and cannot resume, and that all listed
unconfirmed PRs are unrelated work, then enter a reason. The review record and PR head
SHAs are preserved, and the request is rejected if work is in progress or PR
information changed after the review.
After the review, GitHub is queried again and cleanup continues under the existing
24-hour retention rule. Session creation is not retried and the original test result
does not change. Review cannot lift protection from confirmed test PRs, and new
unconfirmed PRs or changed heads must be reviewed again.

A single `System maintenance` schedule per installation continues unfinished tests and
cleanup even after the page is closed. No per-test schedules are created. The internal
minimum interval is 60 seconds, and the deployment's external 5-minute tick remains.
The deployment's dispatcher trigger must run, and **Check / continue now** also advances
progress manually.
This shared schedule is shown as `System Managed` and cannot be created, changed,
deleted, or paused from the regular UI/API; to stop an individual test, use **Cancel
test** in Connections. Even if a connector is replaced on the project or catalog, the
previous connector cannot be deleted while an in-progress test or unfinished cleanup
references it. Once cleanup completes, a connector with no other references can be
deleted.
Queries and re-entering the page do not create PRs or comments. Each project allows one
concurrent test, and restarts and duplicate calls are handled with the start request ID,
dedicated branch, comment marker, and DB lease.
Tests also follow the selected catalog's usage and concurrency limits. Diagnostic runs
are separate from development runs but are recorded only once in the quota ledger. If
termination of canceled remote work cannot be confirmed, capacity is conservatively
held for up to 24 hours after termination. Once remote execution completion is
confirmed, execution capacity is returned regardless of CI waits or cleanup errors.
Codex treats the first `chatgpt-codex-connector` reply after the test mention as the end
of the cloud task, including replies confirmed late during cleanup after cancellation or
failure. If no verification push appears within 5 minutes of the reply, the test ends as
failed (for example, `GH_TOKEN` rejected by the environment). The Jules session creation
intent is saved before the external request, so on a lost response or restart the
existing session is found by its unique title and the creation request is not resent.
Even if the process exits right before the request, duplicate prevention takes priority
and the test may end in a timeout. No additional mentions are sent on usage limits or no
response.

When project settings change or the project is deactivated, in-progress tests end and
are cleaned up using the repository and connector from creation time. Catalog connector
replacement, credential refresh, and active state, as well as repository and CI contract
changes, are also detected. Previous results are kept and re-verification is recommended.
Name or usage/quota updates alone do not mark verification results as stale.
Hub cannot detect changes to Cloud setup itself. Projects with test history cannot be
deleted, to preserve evidence.

## Rollout

Apply DB migrations `c1a2b3d4e5f6`, `d2b3c4d5e6f7`, and `f4d5e6f7a8b9`
(`just db-upgrade`). Existing data and projects' default auto-merge settings are not
changed. The last migration converts existing per-test schedules and auto-created Jules
syncs into the shared schedule and preserves test, session, and job history. The GitHub
connector used for tests needs Contents and Pull requests read/write permissions to open
and close PRs and to create and delete the dedicated branch.

The Jules API contract follows the official [Sessions](https://jules.google/docs/api/reference/sessions)
and [Sources](https://jules.google/docs/api/reference/sources) references. Automated
verification mocks the HTTP boundary; real account connections and the PR base and CI
behavior Jules chooses must be confirmed after deployment with a first PR test in
Connections.

## Per-provider extension structure

Each adapter defines required settings, verification method, per-step display, and result
links. The UI reads the definitions from `connection-tests/options` to show guidance and
whether a test can start. Items that must be set up externally, such as Codex Cloud, are
distinguished from connector items the Hub can verify. New test methods are added by
registering an adapter and adding its definition, without adding provider conditionals
to the shared execution engine or UI. Quota policy and real work execution support for
a new catalog kind follow the existing catalog extension procedure.

Jules Source lookup and the API client are shared by diagnostics and regular work. Codex
usage-limit responses are classified the same way as real development mentions and are
reflected in the catalog's quota state.
