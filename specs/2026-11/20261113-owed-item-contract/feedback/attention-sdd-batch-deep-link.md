---
id: FB-attention-sdd-batch-deep-link
title: Deep-link the Attention SDD batch action to the batch itself
scope: repo
kind: suggestion
category: missing-capability
target: modules/hub-ui/src/lib/features/attention/owed-links.ts and the project Repository tab (UX-sdd-batch)
origin: agent
severity: workaround
recurring: false
status: open
created_at: 2026-11-13
---

# [FB-attention-sdd-batch-deep-link] Deep-link the Attention SDD batch action to the batch itself

Deferred from the Phase 2b review of `UX-attention` (finding R4).

## 2. Suggestion / Change Request (suggestion, change-request)

- **Current Procedure**: The "Inspect batch" action on an `sdd-batch-attention` owed item opens the owning
  project's Repository tab (`/projects/<id>?tab=repository`). The tab shows batches only after the operator loads
  the retained batches, and it has no anchor for one batch, so the operator finds the batch by hand.
- **Proposed Procedure**: Give the Repository tab a batch anchor (for example `#sdd-batch-<id>`) that loads the
  retained batches and scrolls to the named one, then map `context.sdd_batch_id` to it in `owed-links.ts`, as Work
  Plans and Work Items already are (`#work-plan-<id>`, `#work-item-<id>`).
- **Expected Benefit**: Every owed kind opens its exact subject; the batch's attention and cause are one click away.
- **Cost & Risk**: A Repository tab change (load-on-anchor and scroll) plus a link mapping and tests; low risk.
- **Attempted**: Hypothesis. Restart when the Repository tab or `UX-sdd-batch` next changes; acceptance: the
  Attention "Inspect batch" link names the batch and the tab opens with that batch visible, covered by
  `owed-links.test.ts` and a Repository tab integration test; then update the `UX-attention` Interactions row.

## Evidence

```text
owed-links.ts: case 'sdd-batch-attention' returns projectTabHref(project_id, 'repository') without the batch id.
AttentionView.integration.test.ts: sdd-batch-attention row expects /projects/<id>?tab=repository.
```
