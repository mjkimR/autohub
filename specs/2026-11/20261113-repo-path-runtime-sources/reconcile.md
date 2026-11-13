---
reconcile_id: REC-repo-path-runtime-sources
status: resolved
targets:
  - file: docs/capabilities/sdd/CAP-SDD-runtime-isolation.md
    resolution: modified
  - file: docs/operations/sdd-runtime.md
    resolution: modified
  - file: docs/architecture/ARCH-11-risks-and-technical-debt.md
    resolution: modified
  - file: docs/steering/glossary.md
    resolution: modified
  - file: docs/decisions/2026-11/20261113-repository-path-sources.md
    resolution: modified
  - file: docs/decisions/2026-11/20261113-repository-locked-runtime.md
    resolution: modified
---

# Reconcile: SPEC-repo-path-runtime-sources

`ADR-repository-path-sources` records the decision and supersedes the identity clause of
`ADR-repository-locked-runtime` in part (pointer line only). `CAP-SDD-runtime-isolation` restates it: the summary,
Scope Excluded, rule 2 (identity covers path source digests), rule 4 (path refusals), rule 9 (Git or path builds),
the new rule 32 (Hub-process capture within 10,000 files and 32 MiB), the identity document, install steps 1 and 3
and the refusal table. The operations guide states the consumer requirements and troubleshooting actions,
`ARCH-11-risks-and-technical-debt` extends the accepted self-judging risk to in-repository bundles, and the glossary
entry for Runtime identity names the path source content.

No impact: `UC-start-sdd-activity` and `UC-complete-sdd-workflow` cite the refusal codes and the capability without
restating which sources are supported, so their steps and extensions stay accurate; `ADR-offline-source-build` stays
in force unchanged because path sources need no fetch and use its sandboxed build step. The capability's entrypoints
already list `lock_runtime.py` and `runtime_install.py`. No source feedback or deferred work.
