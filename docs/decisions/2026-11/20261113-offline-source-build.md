---
id: ADR-offline-source-build
title: Build locked sources offline after Hub-side fetch
summary: For installing private Git sources without wheels, we fetch them in the Hub process with the project's connector token and build them in the sandbox without network or credentials, to keep build code away from tokens and metadata, accepting a more complex install.
proposal: SPEC-repo-locked-sdd-runtime
status: accepted
created_at: 2026-11-13
---

# [ADR-offline-source-build] Build locked sources offline after Hub-side fetch

Superseded in part by `ADR-repository-owned-sdd-execution`: all decisions assigning source fetch, build and isolated evaluation to Hub.

- **Status**: Accepted
- **Date**: 2026-11-13

---

## 1. Context & Problem Statement

Installing from a repository lock (`ADR-repository-locked-runtime`) must fetch private Git sources such as
devkit and g-tools. They ship no wheels, so installation runs their build backends. Evaluation today runs
repository code with no network and no host credentials (`CAP-SDD-runtime-isolation` rule 22). A network-enabled
sandbox with a token would give build code that token and access to the Cloud Run metadata server, whose
service-account token reaches Hub's secrets.

## 2. Decision Drivers

- Build code never reads a credential or the metadata server.
- Credential scope matches the project, with no per-source grants by an operator.
- Installation remains feasible with uv and the image's toolchain.

## 3. Considered Options

1. Sandbox install with network egress and a dedicated read-only source token: simplest, but exposes the token and metadata to build code and needs grants per new source.
2. Hub-side fetch of Git sources with the project's connector token, then sandbox builds without network or credentials, network only for registry downloads.
3. Hub-side download of every artifact, then a fully offline sandbox install: strongest isolation, more Hub-side logic.

## 4. Decision Outcome

Chosen option: 2, with option 3 as the fallback when uv cannot separate registry download from source builds,
because it keeps build code away from credentials and metadata while reusing the connector token the checkout
already uses.

- Private Git sources are fetched in the Hub process with the project's GitHub connector token; the token never enters the sandbox. → `CAP-SDD-runtime-isolation` rule 8 (MUST)
- Source builds run in the sandbox without network or credentials, using build backends pinned in the image. → `CAP-SDD-runtime-isolation` rule 9 (MUST)
- Network inside the install sandbox, if any, serves registry artifact downloads only. → `CAP-SDD-runtime-isolation` rule 9 (MUST)
- Evaluation keeps no network and no credentials. → `CAP-SDD-runtime-isolation` rule 22 (MUST)

## 5. Consequences

- Positive: no shared source token to provision or leak; per-project credential scope.
- Negative: Hub owns source fetching and pinned build backends; a repository whose sources need other backends is refused until the image provides them.
- Follow-up: Development verifies whether uv can separate registry download from source builds; if not, it implements option 3.

## 6. Confirmation

Tests planned in the handed-off spec that a build step cannot reach the network or read a credential, and that the
connector token never appears in the sandbox environment or diagnostics.
