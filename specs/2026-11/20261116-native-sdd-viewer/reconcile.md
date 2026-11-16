---
reconcile_id: REC-native-sdd-viewer
status: resolved
targets:
- file: docs/architecture/ARCH-02-constraints.md
  resolution: modified
- file: docs/architecture/ARCH-05-1-containers.md
  resolution: modified
- file: docs/architecture/ARCH-05-2-components.md
  resolution: modified
- file: docs/capabilities/repository/CAP-DOC-repository-viewer.md
  resolution: modified
- file: docs/decisions/2026-11/20261105-sdd-development.md
  resolution: modified
- file: docs/decisions/2026-11/20261116-native-sdd-viewer.md
  resolution: modified
- file: docs/development/toolchain.md
  resolution: modified
- file: docs/usecases/repository/UC-inspect-repository-documents.md
  resolution: modified
- file: docs/ux/repository/UX-repository.md
  resolution: modified
- file: docs/ux/sdd/UX-sdd-proposals.md
  resolution: modified
---

# Native repository viewer reconciliation

Hub owns repository presentation, native document/index rendering, release handbook and roadmap. Backend wire contracts and activity execution authority are unchanged. The viewer artifact and its provenance checks are removed; Python devkit pin guarantees remain.

No required criteria are deferred. Dashboard summaries and unsupported Shared/local overlay surfaces are explicit non-goals, not future delivery promises.

NativeSddViewer is the UI doorway through RepositoryView. Existing backend API/service entrypoints remain the capability doorways; helper and test files are not entrypoints.

Independent reconciliation verified all targets without findings. The implementer verified the final Mermaid sandbox layout adjustment against the same contracts; it adds no document target. Repository/toolchain/manifest candidates from entrypoint derivation were rejected because they are not inspection doorways.
