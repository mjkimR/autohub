---
id: PLAN-pending-decision-count
spec: SPEC-pending-decision-count
---

# Technical Plan: `SPEC-pending-decision-count` Exact pending-decision count

## 1. Constitution & Invariant Review

None. The change keeps `Router → UseCase → Service → Repository` with `Annotated[..., Depends()]`, adds no table,
index or migration, and keeps the shared-database rule of one connection per request with no session held across
external I/O and no nested `AsyncTransaction`. `CAP-PR-operator-decisions` documents the list response fields and is
updated in spec-sync; `CAP-MCP-tool-access` lists `decisions_list` without its fields and needs no change. No ADR is
needed: an additive response field follows the existing list conventions.

## 2. Architecture Overview & Impact

### API shape decision

Chosen: an additive required field `actionable_total_count: int` on the existing `DecisionPage` response of
`GET /api/v1/pipeline-runs/decisions` (and therefore of the MCP `decisions_list` tool, which returns `DecisionPage`).

- **Smallest contract change**: no new route, schema, MCP tool, router ordering concern or authorization surface;
  existing clients ignore the extra field.
- **Existing convention**: list responses already carry totals as `total_count` or qualified
  `<qualifier>_total_count` (`event_total_count`, `history_total_count`); the qualifier states that only actionable
  rows are counted.
- **Filter consistency by construction**: the count is built from the same filter function as the page, so it
  cannot drift from the list semantics.
- **Cost**: one extra aggregate statement per list call, in the same transaction and connection. The projection is
  small and bounded by pending decisions on nonterminal Runs.

Rejected: `GET /pipeline-runs/decisions/count`. It saves one row read per shell check but adds a route, response
schema, typed-client path and a second definition of the filter contract to document and keep in step.

### Impacted components

| Layer | File | Change |
| --- | --- | --- |
| Schema | `modules/hub/app/features/project_management/pipeline_runs/discovery_schemas.py` | `DecisionPage.actionable_total_count: int` |
| Repository | `modules/hub/app/features/project_management/pipeline_runs/discovery_repo.py` | shared `_filtered` statement builder; `count_actionable(session, project_id, kind, question_state)` |
| Service | `modules/hub/app/features/project_management/pipeline_runs/discovery_service.py` | `page_result(rows, limit, filters, actionable_total_count)` |
| UseCase | `modules/hub/app/features/project_management/pipeline_runs/usecases/discovery.py` | `list` reads page and count in its single `AsyncTransaction` |
| Router | `modules/hub/app/features/project_management/pipeline_runs/api/v1.py` | unchanged (response model carries the field) |
| Typed client | `modules/hub-ui/src/lib/api/generated/` | regenerated with `just gen-ui-api` |
| Shell store | `modules/hub-ui/src/lib/features/project-management/pipeline-runs/pending-decisions.svelte.ts` | read `limit=1`, use the exact count; drop lower bound and sample constant |
| Shell view | `modules/hub-ui/src/lib/components/shared/AppShell.svelte` | unchanged unless an import of a removed name breaks |

## 3. Component & Interface Design

```text
GET /decisions ─▶ DecisionDiscoveryUseCase.list
                   └─ async with AsyncTransaction() as session:      # one connection
                        ProjectRepository.get (when project_id)
                        DecisionDiscoveryRepository.page(...)        # limit + 1 keyset rows
                        DecisionDiscoveryRepository.count_actionable(...)  # SELECT count(*)
                        page_result(rows, limit, filters, total)
```

```python
class DecisionPage(BaseModel):
    items: list[DecisionEntryRead]
    has_more: bool
    next_cursor: str | None
    actionable_total_count: int
```

`count_actionable` runs `SELECT count(DecisionEntry.key)` over the same joins (`PipelineRun` nonterminal,
`Project` present) and optional filters as `page`, plus `DecisionEntry.actionable IS TRUE`, without cursor,
ordering or limit.

Frontend:

```ts
export type PendingDecisionCount = { status: 'unknown' } | { status: 'known'; count: number };
export function summarizePendingDecisions(page: { actionable_total_count: number }): PendingDecisionCount;
```

`pendingDecisionText` returns `String(count)` for counts above zero; `pendingDecisionPhrase` returns
"N pending decisions" / "1 pending decision".

## 4. Error Handling & Edge Cases

- Unknown `project_id` (404) and invalid cursor (422) are raised before any count statement, as today.
- A cursor page reports the same total as the first page because the count ignores the cursor.
- Read-committed isolation may let a concurrent owner change land between the page and the count; the next check
  converges. No lock is taken.
- Shell: a failed request or missing data keeps `unknown` (neutral); a stale session generation discards the
  result as today.

## 5. Verification & Test Plan

- Backend integration (`modules/hub/tests/integration/features/project_management/pipeline_runs/test_discovery.py`):
  AC-01 (105 rows, `limit=1` and cursor page), AC-02 (publication pending, answered, dismissed), AC-03 (filters,
  empty filter, 404/422), AC-04 (page and count share one session object and the count runs once; `github.paths`
  stays empty). Run with `just test <path>` (SQLite) and `just test-pg <path>` (PostgreSQL) because the aggregate
  and boolean predicate are dialect-sensitive.
- MCP: `just test tests/integration/mcp` to confirm `decisions_list` still validates its output.
- Frontend: `pending-decisions.test.ts` (count rules) and `AppShell.integration.test.ts` (owed exact count, zero,
  error, failure, loading; request uses `limit: 1`) via `just test-ui`.
- AC-07: `just gen-ui-api` then `just check-ui-api`.
- Repository gates: `just lint`, `just check`, `uv run devkit rules check`.
