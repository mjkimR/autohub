---
id: SPEC-repo-path-runtime-sources
title: Install repository-local path sources in the SDD runtime
summary: SDD runtime selection accepts dependency-group path and editable sources that resolve inside the evaluated checkout, so in-repository and snapshot bundles install like Git sources instead of being refused.
status: planned
created: 2026-11-13
related_capabilities: []
related_usecases: []
workflow: sdd-spec-feature
---
<!-- devkit:skeleton -->

# [SPEC-repo-path-runtime-sources] Install repository-local path sources in the SDD runtime

## 1. Problem Statement & Motivation

Agreed intent (user): repositories install their own devkit bundles, developed in the repository or copied with
`devkit bundle snapshot` (devkit ADR-bundle-source-snapshots), as editable path packages in the dev dependency group
(devkit CAP-DIST-in-repo-bundles). Auto Hub's lock-derived SDD runtime (`SPEC-repo-locked-sdd-runtime`,
`CAP-SDD-runtime-isolation`) refuses every path or editable requirement with `SDD_RUNTIME_SOURCE_UNSUPPORTED`, so any
repository with an in-repository bundle cannot be evaluated. Accept path and editable sources that resolve inside the
evaluated checkout, build and install them like locked Git sources (sandboxed, offline), and include their content in
the runtime identity. Paths outside the checkout stay refused.

## 2. User Stories

- **US-1**: As a developer/agent, I want to implement Install repository-local path sources in the SDD runtime so that system capabilities are extended.

## 3. Non-Goals

1. **Scope Excluded**: <what this change will not do>

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] <scenario>
- **Given** <precondition>
- **When** <action>
- **Then** <expected result>
