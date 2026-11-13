# Architecture

| arc42 section | Document ID and subject |
| --- | --- |
| 2. Constraints | `ARCH-02-constraints`: dependency, transaction, credential and compatibility boundaries with checks or review ownership |
| 3. System scope/context | `ARCH-03-system-context`: actors, external systems and authority boundaries |
| 5. Building blocks | `ARCH-05-1-containers`: backend, SPA, database, coding providers and SDK |
| 5. Components | `ARCH-05-2-components`: internal coordinators, provider ports, registries and UI integration points |
| 6. Runtime | `ARCH-06-execution`: execution paths, checkpoints and recovery sequences |
| 7. Deployment | `ARCH-07-deployment`: image composition, retirement migrations, database namespace and repository-owned execution boundary |
| 8. Cross-cutting concepts | `ARCH-08-crosscutting-concepts`: shared identity, fencing, authority, secret and error boundaries |
| 10. Quality requirements | `ARCH-10-quality-requirements`: measurable scenarios and their enforcing checks |
| 11. Risks and technical debt | `ARCH-11-risks-and-technical-debt`: active constraints, consequences, treatments and reopening conditions |

Capability contracts own feature guarantees; [development](../development/README.md)
owns contributor instructions and [operations](../operations/README.md) owns
serving-host/client procedures. [Deployment status](../operations/deployment-status.md)
records tested/deployed scope. Decisions belong in ADRs when a retained decision
needs one; terminology is maintained in [the glossary](../steering/glossary.md).
