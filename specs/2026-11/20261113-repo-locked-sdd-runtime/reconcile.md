---
reconcile_id: REC-repo-locked-sdd-runtime
status: pending
targets:
  - file: docs/capabilities/sdd/CAP-SDD-runtime-isolation.md
    resolution: modified
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
    resolution: modified
  - file: docs/capabilities/sdk/CAP-SDK-existing-pr-bridge.md
    resolution: modified
  - file: docs/usecases/sdd/UC-start-sdd-activity.md
    resolution: modified
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-execution.md
    resolution: modified
  - file: docs/architecture/ARCH-05-1-containers.md
    resolution: modified
  - file: docs/architecture/ARCH-07-deployment.md
    resolution: modified
  - file: docs/architecture/ARCH-08-crosscutting-concepts.md
    resolution: modified
  - file: docs/architecture/ARCH-10-quality-requirements.md
    resolution: modified
  - file: docs/architecture/ARCH-11-risks-and-technical-debt.md
    resolution: modified
  - file: docs/operations/sdd-runtime.md
    resolution: modified
  - file: docs/operations/execution-targets.md
    resolution: modified
  - file: docs/operations/cloud-run-deployment.md
    resolution: modified
  - file: docs/operations/deployment-status.md
    resolution: modified
  - file: docs/development/testing.md
    resolution: modified
  - file: docs/development/toolchain.md
    resolution: modified
  - file: README.md
    resolution: modified
  - file: docs/architecture/README.md
    resolution: modified
  - file: docs/operations/README.md
    resolution: modified
  - file: docs/steering/glossary.md
    resolution: modified
  - file: docs/decisions/2026-11/20261113-repository-locked-runtime.md
    resolution: modified
  - file: docs/decisions/2026-11/20261113-offline-source-build.md
    resolution: modified
---

# Reconcile: SPEC-repo-locked-sdd-runtime

`CAP-SDD-runtime-isolation` restates the repository-locked runtime contract from
`ADR-repository-locked-runtime` and `ADR-offline-source-build`; the other targets
remove server runtime profiles and describe the lock-derived runtime, its cache,
the host probe and rollout settlement. `UC-execute-sdd-batch` and
`UC-decide-sdd-proposal` cite the capability without rule numbers or profile
terms, so they need no change.

## Findings raised while drafting

Drafting from code surfaced gaps that returned the unit to `build-verify`
(`decisions/02-return-build-verify.yaml`); each is now fixed in code or text:

- The SDK bridge reported HTTP 503 `SDD_RUNTIME_PREPARING` as the terminal
  `workflow-evaluation-failed`; it now propagates as the retryable
  `bridge-unavailable` (`CAP-SDD-runtime-isolation` rule 6, `CAP-SDK-existing-pr-bridge`).
- A running native run blocked on the retry-safe `SDD_RUNTIME_PREPARING`; it now
  keeps its state and is inspected again (`UC-complete-sdd-workflow` 3e,
  SDD-COMPLETE-26).
- `.github/workflows/ci.yml` (`sdd-contract`) installed the removed app-common
  profile; it now installs the seed runtime and `config/sdd-build`.
- Workflow-pin tests deleted with the profile tests are restored in
  `test_contracts.py` and cited by rules 21 and 29.
- The architecture and operations index rows and the `spec.md` rule citation are
  corrected; "Runtime identity" is added to the glossary.

Reconcile check round 1 found further reflection gaps, fixed in text: Development
also evaluates the base before creating its branch (`UC-start-sdd-activity`), the ADR
traces now name the implementing rules (reference repair only, no decision change),
and `CAP-SDD-runtime-isolation` section 4 states the fetch environment, the
`SDD_RUNTIME_PREPARING` exception to blocking, the `SDD_ISOLATION_UNAVAILABLE`
projection and the unreadable-head status.

Known test gap: `CAP-SDD-runtime-isolation` rule 1 states which commit each path
evaluates (base for activity starts, PR head, milestone ref, operator checkout,
default-branch head); the source shows each path passing that commit to its
checkout, but no dedicated per-path test asserts it. Rule 1's Check line cites
selection and identity tests only.

A refused activity start replayed with the same request ID returns the recorded
refusal without its code; this predates the change and applies to every refusal,
so it is left unchanged.

## Deferred work

None.
