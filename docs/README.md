# Documentation Guide

Auto Hub is expanding the existing Scheduler Manager into a development automation service.
These documents explicitly distinguish between design goals and current functionality.

1. [Architecture](architecture.md): Responsibility boundaries and the scope of the core engine.
2. [CI Connection Contract](ci-contract.md): Configuration required when connecting a repository and current observation APIs.
3. [Codex PR Mention Protocol](codex-pr-mention.md): Design contract for dispatching Codex cloud work through PR comments.
4. [Delivery Status](delivery-status.md): Current delivery state, latest validation, and remaining deployment checks.
5. [AI Catalog Gateway](ai-catalogs.md): Per-kind quota policies (Codex, Jules), dispatch ledger, execution adapters, Jules session work types, catalog designation, and project agent schedules.
6. [AI Catalog Implementation Notes](ai-catalog-implementation-notes.md): Module map, admission and session flows, design decisions, extension points, tests, and known limitations.
7. [Operator Notices](operator-notices.md): Notification channels (Telegram), what the hub announces, the scheduler trigger heartbeat, and webhook delivery replay.
8. [Development & Operations](development.md): Commands, testing, and constraints of the existing scheduler foundation.
9. [Code Hygiene Review](code-hygiene-review.md): 2026-09-21 review, applied fixes, structural findings, and test follow-ups.
10. [Project detail and connection tests](project-detail-and-connection-tests.md): Project tabs, catalog-specific Codex/Jules PR verification, merge exclusion, and cleanup behavior.
11. [Work plans and dependencies — design](work-plans-design.md): Agreed Plan/Item ownership, dependency boundaries, pause/revoke behavior, and outbound Issue records.
12. [Work plans](work-plans.md): APIs, controls, retention, outbound GitHub records, and verification boundaries.
13. [MCP](mcp.md): User-level connection, managed credentials, work/operations tools, and deployment status.
14. [MCP distribution review](autohub-distribution-review-2026-09-22.md): MCP-first delivery decision, app-mcp reuse assessment, and implementation review.
15. [Run decisions and recovery](run-decisions.md): Questions, answers, explicit resume, provider markers, idempotency and replacement work.
16. [MCP tool review](mcp-tool-review-2026-09-29.md): Work/operations split and per-tool retain/improve/reconsider ratings (Korean).

[Google login and approval](google-auth.md) describes the implementation, published dependency pins, configuration, and the completed live validation.

[Live Canary Results](canary-results-2026-09-22.md) consolidates the completed Codex/Jules, recovery, approval, and connection-test evidence from 2026-09-21–22. [Work Plan Canary Results](canary-results-2026-09-23.md) covers live work plan execution, immediate follow-up, and Cloud Tasks webhook processing. [Prompt Issue Sync Canary](canary-results-2026-09-28.md) verifies Issue synchronization right after webhook processing, before and after the plan-first ordering fix.

[CI Template Usage](../templates/github-actions/README.md) covers CI setup in target repositories.
The root `justfile` is the single source of truth for commands, and connector credential encryption details are documented in the [Hub module documentation](../modules/hub/README.md#connector-credential-encryption).

When introducing new implementations, update the delivery status alongside the corresponding feature documentation.
Never document APIs or commands as available features before they actually exist.
