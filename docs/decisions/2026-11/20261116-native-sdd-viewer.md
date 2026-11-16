---
id: ADR-native-sdd-viewer
title: Own SDD repository presentation in Hub
summary: "For integrated SDD inspection, we own the repository viewer in Hub to share its theme and navigation, accepting responsibility for document parsing and rendering compatibility."
status: accepted
created_at: 2026-11-16
supersedes: [ADR-sdd-development]
---

# [ADR-native-sdd-viewer] Own SDD repository presentation in Hub

## 1. Context & Problem Statement

The standalone viewer includes independent navigation, theme and optional local-only capabilities. Hub already owns authentication, repository addresses and execution controls. Embedding the full viewer introduces competing navigation and requires a viewer rebuild for every contributor devkit pin update.

## 2. Decision Drivers

- Use Hub's component and theme contracts.
- Keep repository browsing and activity authority separate.
- Preserve selected-branch document interpretation and inspection.

## 3. Considered Options

- Keep the embedded viewer and bridge its theme: smaller initial cost but retains duplicate shell and unsupported surfaces.
- Extract upstream headless parsing: reduces duplication but requires a separately maintained upstream API.
- Own the viewer in Hub: integrates the experience and removes artifact coupling, while Hub maintains document compatibility.

## 4. Decision Outcome

We adopt the Hub-owned viewer.

Supersedes in part `ADR-sdd-development`: viewer receipt review during package updates.

- Hub owns SDD document navigation and rendering through its shared visual system. → `CAP-DOC-repository-viewer` native presentation (MUST)
- Contributor devkit identity checks cover Python source, override and lock consistency independently of the repository UI. → `ARCH-02-constraints` Runtime identity (MUST)
- Repository reads remain descriptive and separate from activity execution authority. → `CAP-DOC-repository-viewer` rule 10 (MUST)

## 5. Consequences

The viewer can evolve with Hub without tarball rebuilds. Hub maintains Markdown sanitization, link resolution and SDD document compatibility. Changes to devkit document formats require fixture review; they do not automatically change Hub presentation.

## 6. Confirmation

Native document and repository integration tests cover inspection and branch isolation. Pin-checker unit tests and just check-devkit validate Python identity. Review confirms no vendor viewer import or artifact remains.
