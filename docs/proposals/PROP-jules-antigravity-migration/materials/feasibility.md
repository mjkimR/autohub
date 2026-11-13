---
title: Antigravity migration feasibility evidence
summary: "Official Remote Agents automation evidence, legacy Jules preservation constraints and incoming contract references for the migration direction decision."
---

# Antigravity migration feasibility evidence

Inspected worktree head: `12ad59f43d33346a04d90b35913c1ed2dcb233c4`, based on
`e1a50a8064597d65fd44906f1b65c01ad93c2425`. Official documentation was read on 2026-11-13.
This evidence describes published interfaces and source inspection. No live provider execution, credentials,
production database inventory or fresh product tests were exercised.

## Published execution surfaces

| Surface | Established by official documentation | Missing evidence for Hub |
| --- | --- | --- |
| Remote Agents App/web | Human-operated remote project/conversation creation and continuation in Google-managed environments. | A service-facing create, observe, outcome or reconciliation API. |
| `agy --remote-agent` | Interactive start with a prompt, project selection and resume using `--conversation=<conversation_id>`. Remote sessions exclude `--print`. | Noninteractive create output, machine-readable terminal state, report/PR retrieval, idempotency or lost-response lookup. |
| Local/headless CLI or SDK | Headless execution and API-key/ADC authentication are described for those surfaces. | Evidence that those modes target Remote Agents; substituting them would change execution/deployment scope. |

Primary sources:

- [Remote Agents, CLI tab](https://antigravity.google/docs/remote-agents?tab=cli): Availability, Start a remote agent
  session, Choose a remote project, Resume remote conversations and Features not available. Remote Agents require
  eligible personal Google AI Pro/Ultra accounts; business-account automation is not established.
- [CLI reference](https://antigravity.google/docs/cli/reference/): headless `-p/--print` and the separate
  `--remote-agent` flag.
- [Installation and authentication](https://antigravity.google/docs/install/): Application Default Credentials and
  Gemini API-key workflows; neither is documented there as Remote Agents service authentication.
- [Features](https://antigravity.google/docs/features): Remote Agents access and completion/input notifications.

Inference: these public pages do not establish a supported unattended Hub integration. The absence of an interface
in this searched documentation is not a claim that no private or future interface exists. Resume IDs alone do not
supply an idempotent create or response-loss reconciliation guarantee. No Jules shutdown date is inferred.

## Legacy preservation inventory

| Owner | Evidence | Retirement consequence |
| --- | --- | --- |
| Catalog and session history | `modules/hub/app/features/ai_catalogs/models.py:24`, `:48`, `:69`; `CAP-AGENT-provider-sessions` | Keep catalog/provider identity, session/report/PR relationships and retained-run markers. Foreign keys restrict removal of referenced catalogs/connectors. |
| Scheduled new work | `modules/hub/app/features/project_management/agent_schedules/repos.py:19`; `modules/hub/app/features/ai_catalogs/services.py:26` | Refuse new Jules work explicitly; disabling a catalog is not removing its pending recovery obligations. |
| Independent collection | `modules/hub/app/features/execution/tasks/domains/maintenance/repos.py:55`; `modules/hub/app/features/execution/tasks/domains/maintenance/task.py:89` | Nonterminal sessions and completed tasks with pending PR adoption remain work even without enabled schedules. |
| Uncertain create and report/PR collection | `modules/hub/app/features/execution/tasks/domains/jules/service.py:111`; `CAP-AGENT-provider-sessions` rules 11–22 | Keep original create correlation and no-repeat-create behavior. Preserve stored reports and normal PR delivery ownership. |
| Connection tests | `modules/hub/app/features/project_management/connection_tests/adapters/registry.py:7`; `adapters/jules.py:24`; `adapters/jules_cleanup.py:90`; `CAP-CONN-connection-verification` rules 6, 12–15, 19–20 | Keep recipe recovery, captured credentials and unresolved output protection until explicit safe disposition; registry removal alone breaks old-row advancement. |
| PR delivery refusal | `modules/hub/app/features/project_management/pipeline_runs/adapters/registry.py:12` | Jules never supplies an existing-PR delivery adapter. Do not create a second PR controller when a replacement is added. |
| Run retention | `modules/hub/app/features/execution/tasks/domains/maintenance/history.py:67` | Keep `pipeline_run_retired_at`; a null run link must not cause readoption of a retained session's PR. |

The inventory adds future boundary candidates for connection tests, the pipeline refusal registry, project schema
provider references, schedule system metadata and connection/project contracts. It does not authorize production
edits or establish how many live legacy rows require draining.

## Incoming-reference map

Collected with `uv run devkit docs refs <ID> --direction in -n 0`. All references below are IDs; the full commands
can be rerun at the selected implementation head. Completed work remains historical evidence.

- `CAP-AGENT-provider-sessions`: `ARCH-05-2-components`, `ARCH-11-risks-and-technical-debt`,
  `PROP-jules-antigravity-migration`, `SPEC-schedule-config-ownership`, `SPEC-ux-documentation`,
  `UC-run-agent-session`, `UX-agent-schedules`, `UX-ai-catalogs`, `UX-catalog-sessions`, `UX-project-detail`.
- `CAP-AGENT-catalog-admission`: `ARCH-05-2-components`, `ARCH-11-risks-and-technical-debt`,
  `CAP-AGENT-provider-sessions`, `CAP-CONN-connection-verification`, `CAP-PR-agent-dispatch`, `CAP-PR-owed-items`,
  `CAP-PROJ-project-connections`, `PROP-jules-antigravity-migration`, `REC-owed-item-contract`,
  `SPEC-owed-item-contract`, `SPEC-ux-documentation`, `UC-configure-agent-catalog`, `UX-ai-catalogs`,
  `UX-catalog-availability`, `UX-catalog-codex-refresh`, `UX-catalog-concurrency`, `UX-catalog-connector`,
  `UX-catalog-create`, `UX-catalog-daily-quota`, `UX-connection-tests`.
- `CAP-CONN-connection-verification`: `ARCH-05-2-components`, `ARCH-06-execution`,
  `ARCH-08-crosscutting-concepts`, `ARCH-10-quality-requirements`, `ARCH-11-risks-and-technical-debt`,
  `CAP-AGENT-catalog-admission`, `CAP-AGENT-provider-sessions`, `CAP-PR-owed-items`,
  `CAP-PROJ-project-connections`, `REC-owed-item-contract`, `SPEC-owed-item-contract`, `SPEC-ux-documentation`,
  `UC-verify-project-connection`, `UX-attention`, `UX-connection-tests`, `UX-project-connections`,
  `UX-project-detail`.
- `CAP-PR-pull-request-delivery`: incoming architecture contracts, delivery capability/use-case/UX owners and
  completed specs were queried. The relevant accepted decision is `ADR-work-item-recovery-lineage`; PR delivery
  remains unchanged by either direction. Its incoming references are `ARCH-06-execution`,
  `CAP-WORK-work-plan-execution`, `PLAN-work-item-retry`, `PROP-work-item-retry-target`, `REC-work-item-retry`,
  `SPEC-work-item-replacement` and `SPEC-work-item-retry`.

No provider-specific accepted ADR was found by the Jules/catalog decision search. A selected retirement policy
would warrant a PADR because it changes contracts across feature areas. No such policy is selected in this turn.

## Conditions for restarting replacement Planning

Verify official supported credentials for Hub's execution environment, unattended create and durable identity,
observation/terminal outcomes, report and PR result retrieval, and lost-response reconciliation without a duplicate
create. Map supported quota, cancellation and human-input semantics explicitly rather than assuming Jules parity.
A later live provider test requires its own authorization and remains separate from source/document verification.
