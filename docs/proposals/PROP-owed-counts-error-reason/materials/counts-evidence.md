# Shared counts failure-reason evidence

Source inspected: `e1a50a8064597d65fd44906f1b65c01ad93c2425`.
Inherited from ~~`PROP-hub-ui-shell-polish`~~, retained at `d9cf2ae7ed792ecb8582c07d9f09979f544e26db`.
This records source/test inspection, not test execution or deployed behavior.

`UX-projects` promises that a failed counts read names its reason in the tooltip. At the inspected source,
`ProjectsView.svelte:72` always derives an empty reason when the shared store exists. `owed-counts.svelte.ts:84`
reads only response `data`, and its catch discards exceptions. The resulting unknown value carries no reason.

`ProjectsView.integration.test.ts:229` tests the failure tooltip through a fallback read without the shell store.
The shared-store tests at lines 243 and 263 cover known and initially unknown counts, not a failed shared refresh.
The child therefore needs a failing real-store in-shell regression before the repair, successful recovery coverage
and proof that no extra Projects count request or shell/Attention presentation change is introduced.


## Planning refresh

Re-inspected at `7e780ab7e45757bdf44e6edd330767f62ffd41dc` on the assigned Planning branch.
No reproduction, frontend test, browser or live service verification ran in this turn.

- `owed-counts.svelte.ts:14-22` keeps loading, errors and invalid totals in the same `unknown` value.
  `OwedCountsStore.refresh` at lines 76-91 reads only `data`, catches without retaining a reason and assigns
  the final value under `session.generation`. Its in-flight guard and checked-at clock define existing cadence.
- `ProjectsView.svelte:72` derives an empty error when a shared store exists. Its unavailable-count snippet already
  renders `Needs-you count unavailable: <reason>` when the error is nonempty, for both responsive copies.
- `api/errors.ts:2-18` defines `apiErrorMessage`: it accepts a nonempty string detail or validation `msg` entries
  and otherwise returns the caller's fallback. `api/pagination.ts:5-8` uses this convention in `responseData`.
  The shared store can import the existing helper without changing the API layer.
- `ProjectsView.integration.test.ts:229-240` verifies `Database busy` only without a shared store.
  Lines 243-270 supply a real store but cover known and initially unknown states only.
  `owed-counts.test.ts` exercises pure summarization and phrases, not `OwedCountsStore.refresh` or its session fence.
- `AppShell.integration.test.ts:122-140` covers rejected reads and invalid/missing counts as neutral unknown marks,
  retaining `Owed items unknown` accessible text and tooltip. The shell must continue to use that text rather than
  exposing the Projects-only failure detail.
- `AttentionView.svelte:33-35` uses shared counts only when `value.status` is known. It needs no production edit for
  separate error metadata.
- `UX-projects` Content promises a failure reason for unavailable counts, while its States text and inspected test
  evidence name only the fallback reason. Development should align those passages with the restored shared path.

The planned regression uses the existing real-store context harness with one API error response. Its baseline is
this branch's unchanged product code before the fix, so the Development worker can record Red without checking
out another commit. The proposed repair adds no request and changes no polling, visibility or navigation trigger.
