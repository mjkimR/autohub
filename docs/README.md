# Documentation guide

Use the capability contracts for implemented guarantees and the use cases for
actor goals, alternative outcomes and acceptance examples. They are derived from
source and enforcing tests. A documented test is not a claim that it was executed
or that the code is deployed; [deployment status](runbooks/deployment-status.md)
keeps that evidence separate.

## Read by purpose

| Purpose | Entry point |
| --- | --- |
| Product context and terminology | [Product context](steering/product.md), [glossary](steering/glossary.md) |
| Planned product themes and queued proposals | [Product roadmap](roadmap/README.md) |
| Feature guarantees, interfaces and code entrypoints | [Capabilities](capabilities/README.md) |
| Actor goals and acceptance criteria | [Use cases](usecases/README.md) |
| Shared UX objects, representations and calls to action | [UX object register](steering/ux-objects.md) |
| Color roles, Badge variants and emphasis for hub-ui | [Visual style](steering/visual-style.md) |
| Implemented screens, modals, panels and task-flow links | [UX](ux/README.md) |
| Concept relationships, identities and lifecycles that span contracts | Domain documents: `DOMAIN-pr-run-lineage`, `DOMAIN-work-item-lineage` |
| Implementation mechanisms and persisted formats read back later | Design documents: `DESIGN-sdd-activity-publication`, `DESIGN-credential-sealing`, `DESIGN-decision-notice-collection` |
| System boundaries, runtime structure and constraints | [Architecture](architecture/README.md) |
| Development approach decision | `ADR-sdd-development` |
| Contributor environment, checks and extension work | [Developing Auto Hub](development/README.md) |
| Serving-host and client configuration/recovery procedures | [Runbooks](runbooks/README.md) |
| Routing an observed symptom to its owning contract or procedure | [Operations](operations/README.md) |
| Deployment and notices | [Cloud Run](runbooks/cloud-run-deployment.md), [operator notices](runbooks/operator-notices.md) |
| Recorded local/production verification and rollout gaps | [Deployment status](runbooks/deployment-status.md), [retained evidence](materials/index.md) |

Auto Hub's support for repository-owned SDD activities in connected repositories is defined by
`CAP-SDD-native-delivery`. Its own development approach, installed tooling and
lifecycle are described in [contributor guidance](development/README.md#change-workflow).

## Document ownership

- Put feature guarantees in `docs/capabilities/<area>/CAP-<AREA>-<slug>.md` and
  actor goals in `docs/usecases/<area>/UC-<slug>.md`. Keep their relationships
  reciprocal. Express capability rules as scoped EARS statements and use-case
  acceptance examples as Given/When/Then scenarios.
- Put system structure in numbered arc42 documents under `docs/architecture/`.
  Cite the actual check for a structural constraint, or identify it as review-only.
- Put one operated interface element in each `docs/ux/<area>/UX-<slug>.md`.
  Link its interactions to use-case steps in both directions. Keep shared object
  representations and calls to action in `docs/steering/ux-objects.md`; glossary
  definitions, capability guarantees and task goals retain their existing owners.
- Keep steering context short, with a title and English summary but no document ID.
  Put behavior in capabilities and verification evidence in materials.
- Refer to ID-bearing documents by full ID in prose and relationship fields.
  Ordinary links remain appropriate for code, external sources and ID-free guides.
- Put symptom routing in `docs/operations/OPS-<slug>.md`: each row routes an
  observed symptom and its discriminating evidence to the owning contract or
  runbook section, without restating either.
- Update the owning contract and its use-case examples when behavior changes.
  Runbooks under `docs/runbooks/` carry serving-host/client procedures. Development guides
  cover changing Auto Hub itself. Both refer to the owning contracts rather than
  keeping competing guarantees. Contributor commands follow the root [justfile](../justfile).
- Write documentation in English. Preserve literal UI labels, localized examples
  and the configured language of planning artifacts.

Retain material only when its source identity, observation or uncertainty supports
an active decision or compatibility/deployment claim. Keep dated evidence in
`materials/YYYY-MM/YYYYMMDD-<slug>/report.md`; consolidate overlapping checks and
remove superseded reviews. Keep completed `specs/` records as historical delivery
evidence; do not reconstruct missing approvals or invent decision rationale.
