# Provider connections and diagnostic recovery

Use this guide to configure an installed Hub and check a project's provider
connection. Contracts are owned by `CAP-AGENT-catalog-admission`,
`CAP-AGENT-provider-sessions`, `CAP-CONN-connection-verification` and
`CAP-PR-pull-request-delivery`. A saved connector or ready recipe does not prove
that the remote account can complete work.

## Prepare the project and catalog

1. Apply the deployment's database migrations before configuring accounts.
   For a configured local environment, run `just db-upgrade` from the repository
   root. If default catalogs are missing, check that `e3c4d5e6f7a8` is applied;
   registering another connector does not create a catalog.
2. Configure the project's repository, GitHub connector and required CI jobs in
   **Connections**. Run its read-only GitHub access check. That check creates no
   agent work and does not verify the Codex or Jules environment.
3. Open **Settings → AI Catalogs**. Use a seeded catalog or **Add catalog** with
   a unique key. Connector registration and catalog creation are separate actions.
   Prefer one catalog per provider account so independent local counters do not
   overstate the same account's available capacity.
4. Set concurrency and quota settings to the intended account limits. Seeded
   Jules values (15 concurrent tasks, 100 per rolling day) are initial local
   settings; they are not an entitlement lookup. **Disable** retires a catalog
   from admission; no catalog deletion control is provided.

## Set up Codex

1. Use a GitHub user PAT for the project's connector with Contents and Pull
   requests read/write, plus Issues and Actions read permissions for comments,
   linked requirements and CI observation. The mention test uses that connector's
   GitHub account; selecting a different catalog does not switch the remote account.
2. Connect that GitHub account in Codex and grant access to the repository.
   Configure the repository's cloud environment and setup script.
3. Make `GH_TOKEN` with push access available during the agent phase, and allow
   access to `github.com`. A secret available only to the environment's setup
   phase does not satisfy the connection recipe's agent-phase push requirement.
4. Confirm that `AGENTS.md` lists the repository checks and required CI runs for
   Draft PRs and `.autohub/connection-tests/**` changes.
5. In project PR automation settings, select a catalog with pipeline-delivery
   support. Keep Codex selected when it should repair PRs produced by Jules.

## Set up Jules

1. Connect the repository in Jules and obtain its API key using the provider's
   account setup. Hub resolves the repository's actual Source during preflight.
2. Register **Jules (API Key)** in **Connectors**, placing the API key in
   **Secret Token**. Keep the connector enabled.
3. In **Settings → AI Catalogs**, assign that connector to the intended Jules
   catalog with **Save connector**. **Connect later** permits catalog creation,
   but sessions and connection tests still need usable credentials.
4. In project **Agent Schedules**, choose that Jules catalog and the intended
   `task` or `report` work. Use the project schedule controls; do not edit its
   derived generic scheduler entry. **Run now** makes it due for the next
   dispatcher tick; it does not synchronously start a cloud session.
5. For the Jules connection test, allow Draft PR CI targeting
   `autohub-connection-test/**`. Do not assume a default-branch-only PR filter
   covers the isolated test base.

For PR intake, choose a supported catalog through the Enroll PR selector or
`@auto-run:<catalog-key>`; a provider kind is accepted only when unambiguous.
Jules session work selects its catalog on the agent schedule. These are separate
choices: catalog creation does not select it for a project or schedule.

## Verify the selected connection

1. Open the project's **Connections** tab and **Test AI catalog**. Select the
   intended catalog and review the generated prerequisites. Resolve missing
   connector requirements and check the manual provider/environment requirements.
2. Choose **Start PR test**. Keep its returned record rather than creating a
   competing request. Reads and returning to the page do not create remote work.
3. Let the dispatcher continue it, or use **Check / continue now** to advance a
   claimable step. Keep the external dispatcher trigger running after leaving
   the page.
4. Inspect the test PR/session links, verified head and CI result. Do not manually
   push the verification marker: marker observation cannot prove who pushed it.
5. Check both verification and cleanup. Success applies only to that captured
   project/catalog configuration. Stale or Legacy Codex history does not establish
   the selected current connection; rerun after credential, repository or CI changes.

If delivery waits, inspect the catalog's availability and active execution count.
For a Codex reply without a verification push, read the reply and check the
agent-phase `GH_TOKEN` and network setup. If CI skips the Draft or fixture path,
fix that repository's workflow before repeating verification.

## Cancel or review cleanup

Use **Cancel test** to stop Hub's diagnostic progression. An already dispatched
remote task can still finish. Read the terminal test and its separate cleanup
state; leave shared maintenance running to close owned output and retry cleanup.
Failed/canceled tests keep their isolated branch for at least 24 hours.

If Jules remote output cannot be confirmed, restore provider access first.
Already proven PRs can still be closed through usable GitHub credentials.
Do not delete the captured old connector while unfinished cleanup references it.

Use **Review cleanup** only after checking provider history. Confirm that no
remote work exists, or that it fully ended and cannot resume. Review every listed
unconfirmed PR and its head, mark only unrelated work as unrelated, and enter the
reason. If the request conflicts, refresh the record and review the current
candidate heads or wait for the active worker. An accepted review still performs
another GitHub scan; it does not retry session creation or change the test result.

Do not remove markers or lift Draft to force a diagnostic into development.
Use normal PR work after the connection is verified. Hub's exclusion does not
prevent a person or external GitHub automation from merging a test PR.

## Adjust a Codex availability hold

Use **Settings → AI Catalogs** to set or clear the local reset time. An explicit
future hold also applies while the catalog is disabled; clearing it asserts that
recovery may be reconsidered. Prefer the account's observed reset over a guess.

To copy a blocking reset from the signed-in local Codex account, provide
`HUB_EMAIL`, `HUB_PASSWORD` and either `HUB_API_URL` or both
`HUB_CLOUD_RUN_SERVICE` and `HUB_CLOUD_RUN_REGION` in the process environment.
Then run from the repository root:

```sh
just sync-codex-quota
```

The helper targets `personal-codex`. It requires exactly one identifiable blocking
Codex quota window and otherwise fails closed; use the UI for an explicit reset
when it cannot determine one. It sends the selected reset/source and uses Hub
login credentials to authenticate; it does not send local Codex credentials,
raw quota payloads or run identifiers to Hub. See `scripts/sync-codex-quota.py`.
