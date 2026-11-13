# Product roadmap

The delivered themes strengthen recovery, connect native SDD work across
units and bring human decisions into one task flow. The product purpose is
defined in [Product context](../steering/product.md); `ARCH-03-system-context`
defines execution and authorization ownership.

| Recommended order | Milestone | Outcome |
| --- | --- | --- |
| 1 | `MS-batch-recovery` | Finish a Work Plan after a partial failure while preserving successful work and execution history. |
| 2 | `MS-native-sdd-execution` | Progress selected native SDD units sequentially under repository dependencies and existing approvals. |
| 3 | `MS-operator-decisions` | Find pending questions and approvals across projects and follow each decision through its next permitted step. |

The order records product priority. All three milestones are done and retained
under `_archive/`. Their scope decomposition and direct proposal work are confirmed.
Each milestone's Completion review cites its delivery evidence. Direct proposal
membership lives exclusively in proposal frontmatter; handed-off specs retain
the completed implementation record. Inspect milestones and completed specs with:

```sh
uv run devkit docs list milestone --history --all-namespaces -n 0
uv run devkit docs list spec --history --all-namespaces -n 0
```

The native SDD milestone remains delivery history; its former executable batch
outcome is retired under `ADR-repository-owned-sdd-execution`. Current activity
and retained-history guarantees belong to `CAP-SDD-native-delivery`.

Milestone closure does not establish deployment or live-provider verification.
Milestones frame product outcomes; they do not activate execution or grant
implementation or merge approval.

## Scope

Deployment, pilot operation, production canaries, CI trigger changes, monitoring
and incident detection are outside this roadmap. Pilot findings can inform later
product work without making operational verification a milestone exit condition.

Jules report recollection and provider question support remain candidates when
scheduled Jules work warrants them. SDK execution discovery and parallel flows
remain candidates when external SDK usage warrants them. These conditional
extensions are outside the three milestones and have no committed delivery scope.

Automatic work decomposition and dynamic agent routing are outside these themes.
