# Operations routing

Each `OPS-<slug>` document starts from an observed symptom and routes it, by
discriminating evidence, to the existing owner: a capability or use-case contract,
or the [runbook](../runbooks/README.md) section that holds the executable steps.
Routing documents restate neither the guarantees nor the procedures they cite;
write them with devkit's `operations-writing` instruction.

| Symptom | Routing |
| --- | --- |
| A Cloud Run helper, secret setup or scheduler provisioning stops | `OPS-deployment-helper-refusals` |
| A repository-owned SDD activity start or claim reconciliation is refused or uncertain | `OPS-sdd-activity-start-refusals` |
| An operator cannot obtain or keep a browser session | `OPS-operator-sign-in-refusals` |
| An MCP client cannot connect to, discover or call Hub tools | `OPS-mcp-client-connection-refusals` |
| A project connection test is refused, stalls, fails or leaves cleanup unresolved | `OPS-connection-test-outcomes` |
| An SDK flow run bound to an HTTP worker is refused, waits or fails | `OPS-sdk-worker-run-routing` |
| A GitHub event or `@auto-run` mention does not enroll or advance a PR run | `OPS-webhook-trigger-routing` |
| An expected Telegram operator notice does not arrive | `OPS-operator-notice-absence-routing` |
