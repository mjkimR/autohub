---
id: UC-execute-sdd-batch
title: Execute a selected SDD milestone chain
summary: "A project operator confirms and follows an immutable sequential native SDD selection, controlling future admissions while existing activity owners retain decisions and merge authority."
area: sdd
primary_actor: Project operator
supporting_actors:
  - GitHub
  - devkit runtime
status: active
capabilities:
  - CAP-SDD-native-delivery
  - CAP-SDD-workflow-control
  - CAP-SDD-runtime-isolation
  - CAP-EXEC-scheduling-maintenance
  - CAP-PR-owed-items
entrypoints:
  - modules/hub-ui/src/lib/features/project-management/repositories/SddBatch.svelte
  - modules/hub/app/features/project_management/sdd/api.py
  - modules/hub/app/features/project_management/sdd/batch_usecases.py
---

# [UC-execute-sdd-batch] Execute a selected SDD milestone chain

## 1. Goal

- **Goal**: Retain and follow selected native work through Development without repeating each activity registration.
- **Scope**: Auto Hub sequential SDD batch admission.
- **Trigger**: The operator chooses execution selection or opens a retained batch.
- **Preconditions**: The operator is authenticated. Repository completeness, project setup, dependencies and native eligibility are checked by Hub.

## 2. Main Success Scenario

1. The operator enters explicit execution selection from a complete captured milestone preview or opens retained batch state (`CAP-SDD-native-delivery`, `UX-sdd-batch`).

2. The operator selects supported direct members and inspects their exact order, waiting prerequisites and activity preferences (`CAP-SDD-native-delivery`, `UX-sdd-batch`).

3. The operator confirms immutable through-Development intent and Hub returns the independently rechecked durable receipt (`CAP-SDD-native-delivery`, `CAP-SDD-runtime-isolation`, `UX-sdd-batch`).

4. The operator follows current phase, exact lineage and retained native-owner results through the sequential selection (`CAP-SDD-native-delivery`, `CAP-SDD-workflow-control`, `CAP-EXEC-scheduling-maintenance`, `UX-sdd-batch`).

5. The operator controls future admission while following already admitted work through its existing owner (`CAP-SDD-native-delivery`, `CAP-SDD-workflow-control`, `UX-sdd-batch`).

6. The operator inspects the retained outcome and leaves repository inspection (`CAP-SDD-native-delivery`, `UX-sdd-batch`).

## 3. Extensions

- **2a.** Discovery is incomplete, unknown, unsupported or over its bound: Hub disables execution selection and shows the exact source reason; refresh resumes at step 1. Interface: `UX-sdd-batch`.

- **3a.** The pinned SHA, project binding or immutable membership basis changed: Hub returns a conflict and invalidates selection; a fresh preview resumes at step 1. Interface: `UX-sdd-batch`.

- **3b.** The create response is lost: the panel preserves the same request identity for explicit retry; a matching receipt resumes at step 4. Interface: `UX-sdd-batch`.

- **4a.** Prerequisites remain unfinished or a PROP dependency needs canonical repair: Hub holds the current slot with exact source/lineage evidence; source repair and refresh resume at step 4. Interface: `UX-sdd-batch`.

- **4b.** Native admission has an uncertain outcome: Hub retains the same claim and known artifacts for reconciliation; resolved evidence resumes at step 4. Interface: `UX-sdd-batch`.

- **4c.** An owner fails, is canceled/rejected, or protected evidence changes: Hub retains attention and the exact cause; the operator inspects its owner or stops future admission at step 5. Interface: `UX-attention`, `UX-project-detail`, `UX-sdd-batch`.

- **5a.** A concurrent control changed the revision: Hub returns current state with a conflict; a fresh explicit control resumes at step 5. Interface: `UX-sdd-batch`.

- **5b.** An admission claim won before pause or stop: the panel discloses that its artifacts can still appear; owner inspection resumes at step 4. Interface: `UX-sdd-batch`.

- **6a.** The page reloads or a project/list response becomes obsolete: the operator loads retained batches for the current project; obsolete or older responses are discarded and step 4 resumes. Interface: `UX-sdd-batch`.

## 4. Postconditions

- **Success guarantee**: The immutable selected members retain exact completed SPEC and confirmed owner merge evidence, or the operator's retained future-admission stop and partial results.
- **Minimal guarantee**: Preview/selection grants no approval. A refusal creates no admission; uncertain effects keep their original claim. Pause/stop changes no already delivered native decision and authorizes no replacement.
- **Owed item**: a batch in `attention` is a counted `sdd-batch-attention` owed item unless a claimed run's
  decision describes it (`CAP-PR-owed-items`).

## 5. Acceptance Criteria (Given / When / Then)

Rules used: `CAP-SDD-native-delivery` sequential SDD batch contract owns selection, claims, dependencies, receipts and controls. `CAP-SDD-workflow-control` owns native decisions, `CAP-SDD-runtime-isolation` owns isolated identity evaluation, and `CAP-EXEC-scheduling-maintenance` owns bounded progress and retention.

### SDD-BATCH-01: Deliver the exact selection

- **Covers**: main success scenario.
- **Given**: A complete pinned milestone contains draft A and prerequisite-held B, explicitly selected with retained preferences.
- **When**: The operator confirms and existing owners independently complete their gates and merges.
- **Then**: The exact immutable order progresses one member at a time through Planning where needed and Development; every success retains canonical completed SPEC and confirmed merge evidence.

### SDD-BATCH-02: Discovery is incomplete, unknown, unsupported or over its bound

- **Covers**: 2a.
- **Given**: An incomplete captured preview.
- **When**: The operator opens execution selection.
- **Then**: Selection is disabled and no admission occurs.

### SDD-BATCH-03: The pinned SHA, project binding or immutable membership basis changed

- **Covers**: 3a.
- **Given**: A moved base or changed project binding.
- **When**: The operator confirms the old selection.
- **Then**: A conflict clears stale selection and no claim is admitted.

### SDD-BATCH-04: The create response is lost

- **Covers**: 3b.
- **Given**: A created receipt whose response was lost.
- **When**: The operator retries the same request.
- **Then**: The existing batch is returned without another create.

### SDD-BATCH-05: Prerequisites remain unfinished or a PROP dependency needs canonical repair

- **Covers**: 4a.
- **Given**: A recorded handoff link but an unfinished PROP prerequisite.
- **When**: Maintenance evaluates the next member.
- **Then**: The dependency stays held until exact canonical completed evidence and valid repair exist.

### SDD-BATCH-06: Native admission has an uncertain outcome

- **Covers**: 4b.
- **Given**: A push, PR or enrollment response is uncertain.
- **When**: The operator refreshes retained status.
- **Then**: The same claim and known artifacts remain visible without a replacement start.

### SDD-BATCH-07: An owner fails, is canceled/rejected, or protected evidence changes

- **Covers**: 4c.
- **Given**: A failed native owner or changed protected input.
- **When**: Hub observes the result.
- **Then**: Attention retains the failed member and no later member is automatically admitted.

### SDD-BATCH-08: A concurrent control changed the revision

- **Covers**: 5a.
- **Given**: A later stop won its revision fence.
- **When**: An older resume request is sent or replayed.
- **Then**: The current stop remains effective and the stale request cannot undo it.

### SDD-BATCH-09: An admission claim won before pause or stop

- **Covers**: 5b.
- **Given**: An activity claim admitted before stop.
- **When**: The operator stops future admission.
- **Then**: No later claim starts while the admitted activity retains its existing owner controls.

### SDD-BATCH-10: The page reloads or a project/list response becomes obsolete

- **Covers**: 6a.
- **Given**: A retained batch and a delayed response from another project or revision.
- **When**: The operator reloads or switches project.
- **Then**: Current server state is restored by explicit lookup and the old response cannot overwrite it.

## 6. Evidence boundary

Source and enforcing tests are named in the linked capabilities. Executed checks remain in `SPEC-sdd-milestone-execution`; this use case claims no deployed tick, live provider run or live GitHub merge.
