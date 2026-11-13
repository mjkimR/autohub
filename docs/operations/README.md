# Operating Auto Hub

Use these procedures to configure a serving Hub, connect clients/providers and
investigate deployment or execution problems. Product guarantees belong in the
capabilities and actor flows in the use cases; this directory carries the concrete
operator steps. Changes to Auto Hub itself follow [development](../development/README.md).

Keep repeatable setup, deployment and recovery procedures here. Put dated check
results, revision identities and investigation evidence in
[materials](../materials/index.md); link the report from a procedure when needed.
The deployment-status guide is an index of recorded evidence and rollout gaps,
not a fresh check of the serving environment.

| Operator task | Procedure |
| --- | --- |
| Provision hosting, secrets, queues and external scheduler | [Cloud Run deployment](cloud-run-deployment.md) |
| Operate optimistic SDD activities and retired claims | [SDD activities](sdd-runtime.md) |
| Configure accounts, managed keys, MCP clients and Google login | [Access](access.md) |
| Connect Codex/Jules accounts, select catalogs and verify a repository | [Provider connections](provider-connections.md) |
| Bind generic HTTP workers; inspect bridge retirement | [Execution targets](execution-targets.md) |
| Configure Telegram and inspect heartbeat, deliveries and history | [Operator notices](operator-notices.md) |
| Distinguish recorded deployment from local implementation | [Deployment status](deployment-status.md) |

For work-specific flows, use `UC-configure-project-connection`,
`UC-deliver-pull-request`, `UC-resolve-run-question`, `UC-execute-work-plan`,
`UC-start-sdd-activity`, `UC-decide-sdd-proposal` and `UC-complete-sdd-workflow`.
Their owning CAPs define exact fields, refusals and approval subjects.

Retain the serving revision and actual Run/PR/approval links after live checks.
A successful local test or guide walkthrough is not deployment evidence.
