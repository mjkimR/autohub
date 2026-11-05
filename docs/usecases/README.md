# Use cases

Each use case records one actor goal, its main success scenario, keyed alternative
outcomes and acceptance examples. Its capability relationships name the guarantees
used by that scenario and are recorded on both sides.

| Actor | Goal and use-case ID |
| --- | --- |
| Operator | Configure a repository connection: `UC-configure-project-connection` |
| Operator | Inspect current PR CI: `UC-inspect-pull-request-ci` |
| Operator | Deliver an enrolled PR: `UC-deliver-pull-request` |
| Operator | Resolve a blocked PR question: `UC-resolve-run-question` |
| Operator | Execute a dependent batch: `UC-execute-work-plan` |
| Operator | Configure an account's admission policy: `UC-configure-agent-catalog` |
| Operator | Run scheduled provider work: `UC-run-agent-session` |
| Operator | Verify a repository/provider connection: `UC-verify-project-connection` |
| Project operator | Start a native SDD activity: `UC-start-sdd-activity` |
| Project operator | Decide a native SDD proposal: `UC-decide-sdd-proposal` |
| Project operator | Complete a native workflow: `UC-complete-sdd-workflow` |
| Project operator | Inspect repository documents and lineage: `UC-inspect-repository-documents` |
| Machine client | Execute an admitted task/flow: `UC-execute-task-flow` |
| Delivery coordinator | Resume a verified existing PR: `UC-resume-verified-pr` |
| External scheduler | Dispatch due work: `UC-run-due-work` |
| Operator | Configure operator notices: `UC-configure-operator-notifications` |
| Operator | Access the management console: `UC-access-hub` |
| Operator | Connect scoped Hub tools: `UC-connect-hub-tools` |

Exact payload fields, status/error codes and bounds belong in the owning
[capability](../capabilities/README.md). Scenario examples describe expected
behavior; execution and deployment claims require separate verification evidence.
