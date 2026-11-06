---
id: PROP-mcp-delivery-tools
title: Expose delivery decisions and recovery through MCP
summary: "Expose decision discovery, request outcomes, SDD batch controls and Work Item recovery through scoped MCP tools that reuse their existing business owners."
status: accepted
created_at: 2026-11-06
target_area: capabilities/mcp/
priority: high
size: L
planning_effort: high
dev_effort: high
boundaries:
  owns:
  - modules/hub/app/mcp/
  - modules/hub/tests/integration/mcp/
  - modules/hub/tests/unit/mcp/
  - docs/capabilities/mcp/CAP-MCP-tool-access.md
  - docs/usecases/mcp/UC-connect-hub-tools.md
  excludes:
  - docs/operations/
  - .github/
  - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-mcp-delivery-tools] Expose delivery decisions and recovery through MCP

## 1. Background & Hypothesis

Existing MCP work tools adapt shared UseCases with `machine:<machine UUID>` actors. Completed decision discovery/outcome, batch controls and Item recovery/replacement have no MCP adapters. Operators currently leave their conversational client for these operations.

Expose those owners through a deliberately bounded machine surface. Source inspection is retained in `materials/owner-evidence.md`. No repository or provider is called by discovery/outcome reads. Exact native review is different: it inspects provider/repository evidence and persists a new owner revision, so it is a write operation.

## 2. Technical Spike Questions

- **Q1 resolved**: actor parameters on batch, recovery and replacement owners accept authenticated machine strings. Preserve actor-bound replay; never accept a user/actor field from the client or impersonate a human. No new native proposal acceptance, worker answer or integration approval tool is added.
- **Q2 resolved**: use focused adapters with MCP-specific allowlisted output models, rather than returning raw owner snapshots. See the inventory and output contract below.
- **Q3 resolved**: unknown records stay unknown. Reads do not retry commands, and existing owner revision/idempotency/lease/retention fences remain authoritative.

## 3. Proposed Design & Impact

### Alternatives

| Option | Benefit | Cost / consequence |
| --- | --- | --- |
| A: retain UI-only operations | No transport extension | Conversational operators still switch contexts |
| B: scoped owner adapters with allowlisted views, recommended | Reuses ownership, replay and audit identity | Requires explicit schemas and field projections |
| C: raw owner REST proxy | Small initial adapter | Leaks snapshots and makes mutation/authority semantics implicit |

Choose B. `PADR-mcp-delivery-owner-adapters` records the cross-feature transport decision. No second controller, database migration, native evaluator or identity model is added.

### Fixed tool inventory

All tools are registered only on `/mcp/`. Existing tools and names remain compatible. Descriptions disclose side effects and exact retry requirements.

| Name | Scope / risk | Owner and contract |
| --- | --- | --- |
| `decisions_list` | READ | `DecisionDiscoveryUseCase.list`; optional project/kind/question-state filters, opaque cursor, limit 1–100 |
| `decisions_review` | WRITE | `DecisionDiscoveryUseCase.review`; exact key/fingerprint; persists inspection/CAS and may increment run revision, but never authorizes/resumes execution |
| `runs_decision_outcome` | READ | `DecisionOutcomeUseCase.get`; exact run UUID/request UUID/operation (`question`, `answer`, `resume`) |
| `sdd_batches_list` | READ | `SddBatchUseCase.lists`; latest at most 50 batch summaries, explicit history window |
| `sdd_batches_get` | READ | `SddBatchUseCase.get`; exact project/batch, member status and retained execution links |
| `sdd_batches_control` | WRITE | `SddBatchUseCase.control`; owner `ControlBatch`, request ID and expected revision, pause/resume/stop affect future admission only |
| `work_items_recoveries` | READ | `WorkPlanUseCase.recoveries`; exact project/Plan/Item, offset >=0 and limit 1–100 |
| `work_items_recover` | WRITE | `WorkPlanUseCase.recover`; unchanged strict owner request and authenticated machine actor |
| `work_items_replacements` | READ | `ReplacementUseCase.get`; exact project/Plan/Item, optional candidate and owner history/event paging |
| `work_items_replacement_link` | WRITE | `ReplacementUseCase.mutate(operation="link")`, unchanged revisions/identities |
| `work_items_replacement_accept` | WRITE | `ReplacementUseCase.mutate(operation="accept")` for one existing local edge; no general approval authority |
| `work_items_replacement_withdraw` | WRITE | `ReplacementUseCase.mutate(operation="withdraw")`; consumed evidence remains protected |

READ means `autohub:mcp:read`, WRITE means `autohub:mcp:write`. The registry checks scopes before the handler; discovery itself grants none. Transport revocation and endpoint separation retain `CAP-MCP-tool-access` semantics. A write-only key does not implicitly gain read scope.

Inputs extend the existing MCP `Input` (`extra=forbid`), UUID and page patterns. Reuse strict owner command models instead of re-declaring their validation. Require explicit request IDs and supplied revisions; never generate them, infer an actor from input, refresh-and-retry, or call another mutation after a refusal. Cross-project Plan/Item/batch/run identities are checked by existing owners. Current machine scopes are service-level access, not per-project grants; the adapters add no fabricated per-user project ACL.

### Safe output contract

Return typed MCP views, not `PipelineRunRead`, `BatchRead.basis`, arbitrary `evaluation`, `initial`, `sdd_progress`, recovery `command`/`prior_outcome` or raw replacement `evidence` dictionaries. No credentials, PR bodies or task/answer text are added. Existing owner question-answer tools retain their prior contract.

- Discovery preserves exact key, fingerprint, subject/run/project identity, kind, title, question state, actionable flag, revision/head and age/observation basis. Preserve opaque cursor/has-more.
- Review returns selected key/fingerprint, current run ID/project/state/revision, inspected head/digest and a `requires_reselection` disclosure if supported owner output proves a changed subject. An owner 409 remains a refusal; never return a new subject as success. No approval token or raw owner snapshot is returned.
- Outcomes preserve namespace/request/run identity, unknown/recorded state, observation/current revision/state, attempt/delivery/publication facts, nullable unavailable reason and exact resolved envelope/head evidence. Omit answer text and raw authority/hold payloads; expose authority/hold presence as observed booleans plus safe status/reason fields only where the owner provides them. Historical recorded facts never become current authorization.
- Batch list uses summaries only. Batch detail exposes ordered at-most-50 members, phase/state, IDs and retained latest claim identity/branch/PR number/run ID, uncertainty, total claim count and `history_omitted`. Never claim complete claim history when projecting the latest claim. The 50-row list window is not unbounded pagination.
- Recovery pages retain record/request IDs, actor/reason, revisions, state/detail, timestamps and safe event identity/kind/detail/time. Omit command/prior-outcome/event raw maps.
- Replacement views retain endpoint project-scoped Plan/Item IDs, revisions, states, digests, repository/target/connector and PR/merge/execution identity; link/acceptance IDs, active/consumed flags, actor/reason and paged event identity/revision/kind/time. Omit endpoint specification description/acceptance text and raw event evidence. Preserve active/consumed current evidence independently of history pages and the exact operation result after replay.

Existing owner history/list construction may load more than the public view; this proposal promises bounded returned collections, not a new database work bound. Nested variable collections use explicit caps (100 events, 50 candidate heads, latest claim per member) and carry count/omission disclosure. Truncation never substitutes another identity or converts unknown into failure/success. Strings used as owner diagnostics remain within existing validated owner limits; unsupported structured fields remain absent/null instead of arbitrary serialization.

### Implementation and parallel boundaries

Use new focused MCP modules `decision_inbox.py`, `sdd_batches.py`, `work_item_recovery.py`, `work_item_replacements.py` and a split output-model module as size requires; the nearest existing parent is `modules/hub/app/mcp/`. Wire only `server.py` and explicit dependency construction in `dependencies.py`. Reuse owner calls, not direct repositories or HTTP-to-REST calls. New cross-feature edges outside already declared MCP ownership are out of scope; report a missing declaration rather than bypassing architecture checks.

Add focused tests under the existing MCP integration/unit directories. Living Spec changes are limited to `CAP-MCP-tool-access` and `UC-connect-hub-tools`, plus the promoted PADR's confirmation. Owner capabilities remain unchanged because their semantics are reused. No frontend, generated UI API, migration, schema ownership, notification code or template code changes are expected. This isolates Development from `SPEC-decision-notifications` and `PROP-work-plan-templates`; Host validates exact final task boundaries before parallel handoff.

### Acceptance examples and verification

- **MCP-01**: Given read-only, write-only, revoked and wrong-endpoint credentials, when each new tool is discovered/called, then transport and per-tool scope rules hold and rejected handlers have no effects. `decisions_review` is WRITE even for ordinary subject inspection.
- **MCP-02**: Given exact decision key/fingerprint, when owner review races head/revision/binding changes, then the same CAS and 409 semantics apply; no replacement subject or native authority is submitted.
- **MCP-03**: Given the same request UUID in different run/operation namespaces or an absent retained request, when outcome is read, then evidence never aliases and missing facts stay unknown without provider calls.
- **MCP-04**: Given lost command responses, when same machine/identity/payload replays after state changes, then the existing retained result returns; changed machine/content/route identity conflicts and no duplicate dispatch occurs.
- **MCP-05**: Given stale batch revisions, retired/unsettled claims or stopped batch work, when controlling future admission, then owner holds remain and admitted work is not canceled or approved by proxy.
- **MCP-06**: Given recovery eligibility refusals and replacement role/binding/merge/consumption guards, when invoked by a machine, then exact owner outcomes and original Plan/Item results remain unchanged except the explicitly permitted command.
- **MCP-07**: Given malicious secrets/text inserted in omitted raw owner dictionaries or oversized nested history, when every view is serialized, then only allowlisted fields appear with explicit bounded-history disclosure.
- **MCP-08**: Given existing MCP clients, when using prior tools, then names, output schemas, endpoint split and scope requirements remain compatible. Tool errors preserve existing `{ok,result,error}` semantics and owner error codes; no error is converted into a fresh command.

Development runs new real-handler MCP tests with controlled external services, existing MCP/auth suites, relevant owner replay tests, `just lint` and `just check` after backend initialization. PostgreSQL owner races are reused and extended only when new transport execution exposes a missing case. Planning executes document/envelope checks only. Baseline is the same head with new tool registrations disabled: new tool discovery absent, existing tools unaffected; no timing improvement claim.

### Non-goals

- **Scope Excluded**: batch creation/selection and milestone preview tools, proposal acceptance/handoff/integration authority, native worker-answer mutation tools, new human delegation, implicit approvals/retries, new persistence, OAuth, UI redesign, provider/Jules and SDK flow tools.
- **Scope Excluded**: deployment, live-provider verification, monitoring, CI changes, changes to owner eligibility or machine project authorization.

## 4. Lifecycle & Retirement Criteria

Planning recommends B within the authorized goal; routine machine-adapter and field-projection choices are Host-authorized assumptions. No user-only business question blocks this turn. High Development effort remains appropriate for external MCP contracts and actor/replay boundaries. `CAP-MCP-tool-access`, `UC-connect-hub-tools` and the promoted decision are the reconciliation targets. Direction acceptance and handoff remain Host actions; this branch records neither.
