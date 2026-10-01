# Work Plan backlog and activity

Implementation contract agreed and documented before development on 2026-10-01.
Implemented locally, not deployed; verification is tracked in
[delivery status](delivery-status.md).

## Ownership and entry paths

Repository documents own long-term direction, design and specifications. A Work
Plan owns a concrete seed, its refinement, optional proposal, execution and local
discussion. GitHub Issues remain outbound execution records, not a second backlog.
Most plans are agreed in an external agent conversation and can register directly
for execution. Proposal review is optional, never a mandatory approval gate.

## Lifecycle

| State | Contract |
| --- | --- |
| `draft` | Title required; zero items and incomplete item descriptions/acceptance allowed. No execution or Issue publication. Item membership is editable. |
| `proposed` | Complete, validated plan awaiting a decision. No execution or Issue publication. Editing returns it to draft so the reviewed version is explicit. |
| `paused` | Validated work held from admission. Before first start the UI calls this Ready, otherwise Paused. Existing Runs continue. |
| `active` | Execution requested; reservations, dependencies and capacity still apply. |
| `completed`, `revoked` | Existing terminal semantics. |

Creation accepts an explicit initial state (`draft`, `proposed`, `paused`,
`active`), defaulting to `active` for existing clients. Only draft accepts zero
or incomplete items. Keys, bounds and dependency integrity are always validated.
Adding an item never implicitly submits or starts a draft.

Revision-checked controls add `propose` (draft to proposed), `draft` (withdraw a
proposal), and `ready` (draft/proposed to paused). `resume` also explicitly starts
a draft/proposal after validation; it means the caller already has execution
authorization. `pause` cannot bypass draft/proposal validation. `revoke` withdraws
any nonterminal plan. Never move published or started plans back to draft.

Draft/proposed edits can add/remove items; a proposed edit returns to draft.
Renaming an item in the UI updates its dependents together. Invalid or duplicate
keys cannot replace the last valid key or alter its dependency references.
Entered keys survive other item edits, additions and removals; key edits and
membership changes revalidate all entries. Once every entered key is valid and
unique, the UI applies renames and dependency references together, including
key swaps. Pending input and DOM validation state are never sent to the API.
Active/paused plans retain fixed item keys/membership and all-item-unstarted edit
rules. Exiting draft requires at least one item with title, specification and
acceptance, a valid graph and repository binding. All mutations serialize with
admission using the project and plan locks. Registration retries retain the
original identity/digest, do not duplicate history and never resubmit a proposal.

## Comments and change history

One append-only, paginated activity stream per Plan contains comments and changes.
Changes store server-authenticated actor, time, revision, optional reason and
field-level before/after values (including item membership and dependencies).
Creation and user mutations are recorded in the same transaction as the Plan;
automatic Plan completion is recorded with a system actor. Existing Plans start
recording on their next change; historical edits are not invented.
An accepted update/control records its revision and optional reason even if no
specification or state value changed (`changes={}`). Rejected stale revisions and
registration retries do not add activity entries.

Comments have a client-generated request ID, bounded plain text, authenticated
author and timestamp. Identical retries recover the original comment; different
content with the same ID conflicts. They do not increment the Plan revision,
change specifications, resume work, or answer Run questions. No edit/delete,
threads, mentions, attachments, automatic rollback or GitHub comment sync in this
release. Records follow Plan lifetime and are not removed by Run retention.

The UI presents the specification, items and an expandable activity timeline with
a comments filter and load-more pagination. Before/after details are expandable.
Draft/proposal/ready work is discoverable through list filters; proposed work is
visibly awaiting a decision. REST and MCP expose the same lifecycle and activity
contracts. Machine identity is recorded for MCP; a machine's claimed human name
is never trusted as audit identity.

## Verification

Cover no admission/publication for draft/proposed (including scheduled drafts),
strict activation validation, editable draft graphs, proposal invalidation,
revision races with admission, registration and comment retry identity,
authenticated attribution, atomic audit writes, activity pagination, unchanged
pause/Run behavior, API/MCP parity and UI create/edit/control/activity flows.
Apply the activity migration after the existing start-reservation migration;
validate upgrade/downgrade against PostgreSQL. Downgrade refuses live draft/proposed
plans: first make them ready or revoke them. Downgrade removes activity records.
Deploy database, API and UI together.
