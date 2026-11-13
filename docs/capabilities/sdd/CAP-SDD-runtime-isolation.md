---
id: CAP-SDD-runtime-isolation
title: Retired embedded SDD runtime boundary
summary: "Embedded repository devkit installation, asset restoration and isolated evaluation are retired. The retained ID identifies historical runtime evidence; new activity execution does not require a Hub-provisioned SDD environment."
area: sdd
status: deprecated
usecases: []
entrypoints:
  - modules/hub/app/features/project_management/sdd/execution.py
---

# [CAP-SDD-runtime-isolation] Retired embedded SDD runtime boundary

## 1. Summary

Hub does not install or execute a connected repository's devkit runtime, restore
its managed assets, build its sources or inspect its workflow readiness.
`ADR-repository-owned-sdd-execution` supersedes those runtime decisions.
`CAP-SDD-native-delivery` owns optimistic activity dispatch.

## 2. Scope & Boundary

- **In-Scope**: identification of retired runtime evidence and refusal of legacy
  evaluator authority.
- **Out-of-Scope**: repository setup and correctness belong to the repository and
  working agent. Generic SDK worker isolation belongs to
  `CAP-SDK-task-flow-execution`. Auto Hub's contributor devkit remains repository
  tooling under `ADR-sdd-development`.
- **Scope Excluded**: runtime profiles, lock-derived caches, source downloads,
  build environments, OS-sandbox probes and a replacement remote evaluator.

## 3. Business Rules & Policies

1. **No evaluator**: Hub MUST NOT install or execute repository SDD tooling to admit or progress connected-repository work. Check: serving-source import inspection and retired API tests.
2. **No restoration service**: Hub MUST NOT execute or delegate repository asset restoration through `devkit sync`. Check: implementation-request and packaging inspection.
3. **Historical identity**: WHEN an old snapshot contains a runtime identity, Hub MUST preserve it as historical evidence without resolving or installing that runtime. Check: native history API tests.

## 4. Interfaces & Data Contracts

Old runtime/readiness probe routes, where retained as tombstones, return
`SDD_EXECUTION_RETIRED`. They do not launch installation, sandbox tests or
repository evaluation. Stored `cli_version`, runtime and bundle values are
historical fields only. The serving image needs no SDD cache/build variables,
source-read token or bubblewrap support.

## 5. Verification Boundary

Source/import and serving-image inspection verify absence of the evaluator.
Historical completed specs and dated runtime measurements describe their original
revision; they do not promise a current runtime or live deployment guarantee.
