---
id: PADR-owed-items-aggregate-read
title: Read owed items through one aggregate repository
summary: For the cross-feature owed-item list and counts under the shared 20-connection budget, we read owner models through one read-only aggregate repository with one UNION ALL keyset query and one GROUP BY count per transaction, to keep the shell check cheap, accepting coupling to other features' tables.
proposal: PROP-owed-item-contract
# supersedes: [ADR-<slug>]   # write Supersedes in part `ADR-<slug>`: <the replaced clauses>. in Decision Outcome
status: draft
created_at: 2026-11-13
---

# [PADR-owed-items-aggregate-read] Read owed items through one aggregate repository

- **Status**: Draft
- **Date**: 2026-11-13

---

## 1. Context & Problem Statement

The owed-item read (`PROP-owed-item-contract`) lists and counts items from several features: PR runs and their
decision discovery projection, Work Plans and Work Items, Work Item recoveries and replacements, SDD batches and
connection tests. The backend layering is `Router → UseCase → Service → Repository`, and a cross-feature read would
normally compose through each owner's service. The shell polls the count on every visible tab, and Auto Hub shares one
PostgreSQL with another application under a 20-connection limit, with one connection per request.

## 2. Decision Drivers

- One connection and one transaction per request, with a statement count that does not grow with rows.
- One keyset cursor over every kind, without an in-memory merge across sources.
- Owner features keep sole ownership of their writes and lifecycle rules.
- The mechanical check `RULE-app-router-repo-import` (`ARCH-02-constraints`) forbids only router-to-repository
  imports; the dashboard repository already reads other features' models for its aggregate counts.

## 3. Considered Options

1. **Aggregate repository**: one read-only owed-items repository reads the owner models and issues one `UNION ALL`
   keyset query for a page and one `GROUP BY` count for totals, by kind and by project.
2. **Service composition**: each owner service contributes its kind through its own repository; the owed-items use
   case merges the pages and sums the counts. That costs one list and two count statements per kind (12 to 18 or
   more per request) and a composite cursor holding a position in every source.

## 4. Decision Outcome

Chosen: option 1, on the user's decision. The aggregate repository is read-only and reads only the columns its kind
predicates need. Each owning capability states the predicate that makes its object owed; the aggregate repository
implements those predicates and is the single place they are combined. A predicate that needs code-side evaluation
(the connection-test adapter check) filters a bounded SQL candidate set in the service.

## 5. Consequences

- Good: a fixed number of statements per request in one transaction; the shell count issues aggregates only.
- Good: one keyset cursor (`waiting_since`, `key`) across kinds.
- Bad: the aggregate repository couples to other features' table shapes; a schema change in an owner feature must
  update the owed-item predicate and its tests in the same change.
- Bad: owner predicates exist twice (the owner's own logic and the aggregate SQL); tests must pin that they agree.

## 6. Confirmation

- An acceptance test shows the list and the counts each run in one transaction with a fixed number of statements,
  independent of row counts, and make no provider call.
- Per-kind tests create an owed object through the owner's service and assert it appears with the expected kind, and
  disappears when the owner action resolves it.
- `RULE-app-router-repo-import` still passes; the owed-items router imports no repository.
