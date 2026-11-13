---
id: UC-inspect-repository-documents
title: Inspect repository documents and their executions
summary: "A project operator reads a document or milestone proposal at a selected repository branch and follows its recorded execution links. Inspection leaves repository content, run state and approval unchanged."
area: repository
primary_actor: Project operator
supporting_actors:
  - GitHub
  - Embedded devkit viewer
status: active
capabilities:
  - CAP-DOC-repository-viewer
entrypoints:
  - modules/hub-ui/src/lib/features/project-management/repositories/RepositoryView.svelte
---

# [UC-inspect-repository-documents] Inspect repository documents and their executions

## 1. Goal

- **Goal**: Understand the selected repository document and its recorded execution
  context, so the operator can choose subsequent work from the correct branch.
- **Scope**: Auto Hub repository browser and embedded SDD document viewer.
- **Trigger**: The operator opens a project's repository view.
- **Preconditions**: The operator is authenticated to Auto Hub.

## 2. Main Success Scenario

1. The operator opens the connected project's repository view
   (`CAP-DOC-repository-viewer`, rules 1–2).
   Interface: `UX-repository`.

2. Hub retrieves repository identity and available branches
   (`CAP-DOC-repository-viewer`, rules 1–4).
   Interface: `UX-repository`.

3. The operator selects a branch and a proposal or spec document, directly or
   through a milestone member (`CAP-DOC-repository-viewer`, rules 2, 6).
   Interface: `UX-repository`.

4. Hub displays the selected document from that branch
   (`CAP-DOC-repository-viewer`, rules 2, 5–6).
   Interface: `UX-repository`.

5. Hub retrieves executions related to the selected proposal or spec
   (`CAP-DOC-repository-viewer`, rules 7–8).
   Interface: `UX-sdd-execution`.

6. Hub shows project-scoped run/decision and GitHub PR links for inspection
   (`CAP-DOC-repository-viewer`, rules 7–8).
   Interface: `UX-sdd-execution`.

## 3. Extensions

- **1a.** Project has no GitHub connection: The view asks the operator to connect a
  repository; the use case ends. A direct repository API request is refused with
  HTTP 422 / `INVALID_REQUEST`.
   Interface: `UX-repository`.

- **2a.** Branch enumeration is incomplete: Hub retains the available/default
  branch information with incomplete coverage; the embedded `refs` operation
  reports its incomplete-list error instead of certifying all branches. The
  operator can continue inspecting the known selected ref at step 3.
   Interface: `UX-repository`.

- **3a.** Operator chooses an ordinary file rather than a proposal/spec: Hub shows
  that file without native-unit execution links; the use case reaches its document
  inspection goal at step 4.
   Interface: `UX-repository`.

- **4a.** File content is not decodable UTF-8: The repository response carries
  base64 encoding rather than fabricated text; the Git browser explains that the
  binary file cannot be displayed inline and the use case ends.
   Interface: `UX-repository`.

- **4b.** Repository read is refused or fails: The view exposes the read error and
  retry action; it does not supply a successful document result and the use case ends.
   Interface: `UX-repository`.

- **5a.** No related executions exist: Hub displays the empty execution state;
  the use case reaches its inspection goal without starting a run.
   Interface: `UX-sdd-execution`.

- **5b.** Selection changes before execution links return: Hub ignores the late
  response for the old selection; resumes at step 5 for the current selection.
   Interface: `UX-sdd-execution`.

- **5c.** Execution-link lookup fails: Hub displays the lookup error and retry
  action while retaining the selected document; the use case ends with execution
  context unresolved rather than claiming no runs exist.
   Interface: `UX-sdd-execution`.

## 4. Postconditions

- **Success guarantee**: The operator sees the chosen document or its available
  representation and, for a selected native unit, its project-scoped execution
  context or explicit empty state.
- **Minimal guarantee**: Inspection does not edit the repository, advance a run or
  grant approval. Missing contents, incomplete branch enumeration and failed
  execution lookup are not presented as complete successful evidence.

## 5. Acceptance Criteria (Given / When / Then)

Applicable rules: `CAP-DOC-repository-viewer` rules 1–5 define project-bound reads
and explicit incomplete/binary representation; rules 6–9 define selected-branch
roadmap navigation, lineage, read-only execution links and visible refusal.

### DOC-INSPECT-01: Read a milestone member on the selected branch

- **Covers**: main success scenario.
- **Given**: A milestone in a global or package roadmap root has a direct proposal
  member on the selected activity branch.
- **When**: The operator opens that member.
- **Then**: Its proposal anchor is selected from that branch and its recorded
  project-scoped run and GitHub PR links can be followed without starting work.

### DOC-INSPECT-02: Explain a missing repository binding

- **Covers**: 1a.
- **Given**: The project has no configured GitHub connection.
- **When**: The operator opens the repository view or requests a repository read.
- **Then**: The view requests configuration, or the direct API returns
  `INVALID_REQUEST`, without returning repository contents.

### DOC-INSPECT-03: Disclose incomplete branch enumeration

- **Covers**: 2a.
- **Given**: GitHub branch pagination fails after partial results or reaches its cap.
- **When**: Hub loads repository branches.
- **Then**: `branches_complete` is false and the embedded ref loader reports
  incomplete coverage while a known selected ref remains readable.

### DOC-INSPECT-04: Inspect an ordinary file

- **Covers**: 3a.
- **Given**: The selected file is outside native proposal/spec unit paths.
- **When**: The operator opens it.
- **Then**: Its contents are shown without inventing a bound native execution unit.

### DOC-INSPECT-05: Preserve binary representation

- **Covers**: 4a.
- **Given**: A file does not decode as UTF-8.
- **When**: Its blob is read.
- **Then**: The API marks base64 content; the inspection does not misreport it as
  successfully rendered Markdown.

### DOC-INSPECT-06: Expose a refused read

- **Covers**: 4b.
- **Given**: The authenticated repository API refuses a file read.
- **When**: The embedded viewer requests the file.
- **Then**: The refusal reaches the viewer and no fabricated file replaces it.

### DOC-INSPECT-07: Keep an empty execution list read-only

- **Covers**: 5a.
- **Given**: The selected unit has no project-scoped related executions.
- **When**: Its execution links are loaded.
- **Then**: The empty state is shown without enrolling or advancing work.

### DOC-INSPECT-08: Ignore stale execution responses

- **Covers**: 5b.
- **Given**: A request for the previous selected unit is still pending.
- **When**: The operator selects another unit before that response arrives.
- **Then**: Only the current unit's execution links are displayed.

### DOC-INSPECT-09: Distinguish a failed lookup from no executions

- **Covers**: 5c.
- **Given**: The selected document loaded but its execution lookup fails.
- **When**: Hub presents the result.
- **Then**: The document remains selected and the execution area shows an error
  with retry instead of an empty-success claim.

## 6. Source and Verification Boundary

The backend, embedding and data-source evidence is linked in
`CAP-DOC-repository-viewer`. UI selection/error handling also derives from
[SddRunLinks.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddRunLinks.svelte)
and its [integration tests](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddRunLinks.integration.test.ts).
Binary rendering, missing-project binding and failed-link display are inspected
source paths; the cited tests do not establish complete integration coverage for
all three. No viewer-specific stable error code is introduced by these scenarios.
