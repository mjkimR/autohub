---
id: TASKS-repo-locked-sdd-runtime
spec: SPEC-repo-locked-sdd-runtime
plan: PLAN-repo-locked-sdd-runtime
---

# Task Breakdown: `SPEC-repo-locked-sdd-runtime` Install the SDD evaluation runtime from the repository lock

## Phase 1: Runtime building blocks

- [x] **Task 1.1**: Lock selection, export classification, identity and Python check, with unit tests
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/lock_runtime.py`, `modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py`, `modules/hub/tests/unit/features/project_management/sdd/fixtures/`
  - _Requirements: AC-03, AC-05, AC-06, AC-07_
  - **Verification**: `just test tests/unit/features/project_management/sdd/test_lock_runtime.py`

- [x] **Task 1.2**: Runtime cache with cross-process build locks, leases, failure markers and eviction, with unit tests
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/runtime_cache.py`, `modules/hub/tests/unit/features/project_management/sdd/test_runtime_cache.py`
  - _Requirements: AC-08, AC-13_
  - **Verification**: `just test tests/unit/features/project_management/sdd/test_runtime_cache.py`

- [x] **Task 1.3**: Installer with Hub-side fetch and wheel install, sandboxed offline builds and atomic publish; build isolation command; unit tests
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/runtime_install.py`, `modules/hub/app/features/project_management/sdd/isolation.py`, `modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py`
  - _Requirements: AC-09, AC-10, AC-11_
  - **Verification**: `just test tests/unit/features/project_management/sdd/test_runtime_install.py`

## Phase 2: Wiring

- [x] **Task 2.1**: Lazy runtime resolution in checkout scopes, single-flight background install, git-safe independence, bundle check from the entry, profile removal
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/runtime.py`, `modules/hub/app/features/project_management/sdd/profiles.py`, `modules/hub/app/features/project_management/sdd/checkout.py`, `modules/hub/app/features/project_management/sdd/isolation.py`, `modules/hub/tests/unit/features/project_management/sdd/test_runtime.py`, `modules/hub/tests/unit/features/project_management/sdd/test_profiles.py`, `modules/hub/tests/unit/features/project_management/sdd/test_activities.py`
  - _Requirements: AC-01, AC-02, AC-08, AC-09, AC-12_
  - **Verification**: `just test tests/unit/features/project_management/sdd`

- [x] **Task 2.2**: Identity continuation, batch evidence identity, milestone identity and bridge runtime source
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/services.py`, `modules/hub/app/features/project_management/sdd/batch_evidence.py`, `modules/hub/app/features/project_management/sdd/batch_driver.py`, `modules/hub/app/features/project_management/sdd/milestones.py`, `modules/hub/app/features/execution/flows/bridge.py`, `modules/hub/tests/unit/features/project_management/sdd/test_services.py`, `modules/hub/tests/unit/features/project_management/sdd/test_batch_evidence.py`, `modules/hub/app/features/project_management/sdd/progress.py` (scope extension: a continued run records the new runtime identity on its snapshot)
  - _Requirements: AC-04, AC-15, AC-16_
  - **Verification**: `just test tests/unit/features/project_management/sdd`

- [x] **Task 2.3**: Diagnostics catalog, split runtime status endpoint, regenerated client and UI runtime line
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/diagnostics.py`, `modules/hub/app/features/project_management/sdd/services.py`, `modules/hub/app/features/project_management/sdd/usecases.py`, `modules/hub/app/features/project_management/sdd/api.py`, `modules/hub/app/features/project_management/sdd/schemas.py`, `modules/hub/tests/unit/features/project_management/sdd/test_diagnostics.py`, `modules/hub/tests/unit/features/project_management/sdd/test_services.py`, `modules/hub-ui/src/lib/api/`, `modules/hub-ui/src/lib/features/project-management/repositories/`
  - _Requirements: AC-14, AC-17_
  - **Verification**: `just test tests/unit/features/project_management/sdd`, `just gen-ui-api`, `just test-ui`

## Phase 3: Test seam, image and evidence

- [x] **Task 3.1**: Integration test seam: fixture repositories carry the seed lock, the cache is seeded from `.cache/sdd`, app-common profile tests replaced; network-free sandboxed build test
  - **_Boundary**: `modules/hub/tests/conftest.py`, `modules/hub/tests/integration/features/execution/flows/test_bridge.py`, `modules/hub/tests/integration/features/project_management/sdd/`, `scripts/test-sdd.sh`, `modules/hub/tests/integration/sdd_runtime.py` (scope extension: shared offline seed for fixture repositories), `modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py` (scope extension: the fake GitHub answers the default-branch head the runtime check reads), `docs/capabilities/sdd/CAP-SDD-native-delivery.md` (scope extension: rule 8 check link pointed at the removed profile test)
  - _Requirements: AC-01, AC-02, AC-04, AC-10, AC-12, AC-16_
  - **Verification**: `just install-sdd`, `just test-sdd`, `just test-sdd-pg`

- [x] **Task 3.2**: Serving image and scripts: pinned build environment, `uv` in the runtime stage, profiles and app-common manifest removed, installer generalized
  - **_Boundary**: `docker/hub.Dockerfile`, `docker/helper/deploy_cloud_run.sh`, `config/sdd-build/`, `config/sdd-runtime-app-common/`, `config/sdd-runtime/`, `scripts/install-sdd.py`, `justfile`, `docker/build_hub.sh` (scope extension: the unused private-source build secret was removed), `scripts/check-devkit.py` (scope extension: the pin check listed the removed app-common manifest)
  - _Requirements: AC-10, AC-18_
  - **Verification**: `just install-sdd .cache/sdd-build config/sdd-build`, `docker build -f docker/hub.Dockerfile .` when Docker is available, `just lint`, `just check`

- [x] **Task 3.3**: Cold-install measurement of the g-scavenger-crew lock recorded and the cache byte cap default set from it
  - **_Boundary**: `specs/2026-11/20261113-repo-locked-sdd-runtime/materials/`, `modules/hub/app/features/project_management/sdd/runtime_cache.py`
  - _Requirements: AC-18_
  - **Verification**: `materials/cold-install.md` records seconds and MiB; `just test tests/unit/features/project_management/sdd/test_runtime_cache.py`
