---
reconcile_id: REC-pending-decision-count
status: resolved
targets:
  - file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
    resolution: modified
  - file: docs/ux/navigation/UX-app-shell.md
    resolution: modified
---

# Reconcile: `SPEC-pending-decision-count`

## Reflected changes

- `CAP-PR-operator-decisions` (Pending discovery): a new WHEN rule states that the decision list reports
  `actionable_total_count`, the exact number of actionable rows the `project_id`, `kind` and `question_state`
  filters admit on visible nonterminal Runs, independent of `cursor` and `limit`, read with one aggregate query in
  the page's transaction; publication-pending rows are excluded and the count covers decision-inbox rows only
  (AC-01 to AC-04, non-goal 5). Its checks name the four tests in `test_discovery.py`. The HTTP paragraph lists the
  new response field. Its `entrypoints` add `usecases/discovery.py`, the discovery use case doorway; repository,
  schema, service and test candidates were rejected as non-doorway files.
- `UX-app-shell` (Pending-decision signal): the source reads the list with `limit=1`; the count is the exact
  `actionable_total_count` with no "N+" lower bound or "N or more" phrase; the undecidable-sample neutral state is
  replaced by "a response without a valid count"; `decisions-neutral` no longer lists undecidable; the count-check
  interaction and frontmatter cite `CAP-PR-operator-decisions`; Evidence names the one-row request, exact backlog
  and invalid-count tests (AC-05, AC-06).

## No impact

- `CAP-MCP-tool-access`: `decisions_list` returns `DecisionPage` and gains the field automatically; the capability
  lists the tool without its output fields, so its text stays accurate.
- `UX-decision-inbox`: rows, filters and pagination are unchanged (non-goal 2); its statement that the shell counts
  the rows carrying the attention left rule still holds.
- Use cases: no actor goal, step or extension changed; `UC-access-hub` and `UC-resolve-run-question` cite the screens
  without the count rule.
- `docs/steering/ux-objects.md` and glossary: no new object, representation or domain term.
- Architecture and decisions: no structural change; the API shape choice (additive field instead of a count
  endpoint) is recorded in `PLAN-pending-decision-count` and does not meet the ADR admission criteria.
- Typed client (`modules/hub-ui/src/lib/api/generated/`) and `modules/hub-ui/README.md` are generated or contributor
  material, not Living Spec targets.

## Deferred work

None. Non-goal 5 excludes counting other operator-owed work (Work Plans, Work Item recovery, SDD batches, connection
tests, AI catalog holds) and the dashboard "Needs you" definition; that question belongs to the Host's ongoing
app-wide OOUX review, which owns any broader owed-work aggregate. This Unit defers no agreed scope.
