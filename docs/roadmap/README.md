# Product roadmap

The recommended sequence strengthens recovery, connects native SDD work across
units and brings human decisions into one task flow. The product purpose is
defined in [Product context](../steering/product.md); `ARCH-03-system-context`
defines execution and authorization ownership.

| Recommended order | Milestone | Outcome |
| --- | --- | --- |
| 1 | `MS-batch-recovery` | Finish a Work Plan after a partial failure while preserving successful work and execution history. |
| 2 | `MS-native-sdd-execution` | Progress selected native SDD units sequentially under repository dependencies and existing approvals. |
| 3 | `MS-operator-decisions` | Find pending questions and approvals across projects and follow each decision through its next permitted step. |

This order expresses product priority. Milestone prerequisites are declared only
when one outcome requires another; the three themes can be planned independently.
Direct proposal membership lives exclusively in proposal frontmatter. Discover
members, sizes and unit prerequisites with:

```sh
uv run devkit docs list milestone --all-namespaces -n 0
uv run devkit docs list proposal --all-namespaces -n 0
```

These themes and their draft proposals frame future work. Proposal Planning
settles implementation scope and requirements; no theme activates execution or
grants implementation or merge approval.

## Scope

Deployment, pilot operation, production canaries, CI trigger changes, monitoring
and incident detection are outside this roadmap. Pilot findings can inform later
product work without making operational verification a milestone exit condition.

Jules report recollection and provider question support remain candidates when
scheduled Jules work warrants them. SDK execution discovery and parallel flows
remain candidates when external SDK usage warrants them. These conditional
extensions are outside the three milestones and have no committed delivery scope.

Automatic work decomposition and dynamic agent routing are outside these themes.
