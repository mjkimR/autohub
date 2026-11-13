# Shell polish decomposition evidence

Source inspected: `e1a50a8064597d65fd44906f1b65c01ad93c2425` on `plan-hub-ui-shell-polish`.
This record supports the return of `PROP-hub-ui-shell-polish` to Backlog.
It records source and test inspection, not test execution or deployed behavior.

## Task-kind evidence

| Outcome | Contract and implementation evidence | Classification |
| --- | --- | --- |
| Counts failure reason | `UX-projects` Content tree states that a failed counts read names its reason in the tooltip. `ProjectsView.svelte:72` always derives an empty reason when the shared store exists. `owed-counts.svelte.ts:84` reads only response `data`; its catch discards the exception. The resulting unknown value carries no reason. | `bugfix`: restore an agreed failed-read tooltip contract in the shared-store path. |
| Sidebar overflow cue | `UX-app-shell` promises scrolling the active link into view. `AppShell.svelte:154` renders an overflow container; no edge cue is rendered. The proposed cue adds an observable behavior beyond that contract. | `feature`: expose whether links remain outside the visible navigation area. |

The spec classification and Backlog instructions define `XL` as work requiring multiple task kinds or specs.
A single parent cannot hand both outcomes to one task-kind workflow. The Planning return therefore sets
`needs_decompose: true` and `size: XL` without implementing either outcome.

## Test inspection

`ProjectsView.integration.test.ts:229` checks the error tooltip through the fallback read without a shell store.
The shared-store tests at lines 243 and 263 cover a known count and an initially unknown count, respectively.
They do not fail a shared counts refresh and assert that its reason reaches the tooltip.
No reproduction test, UI test or application verification was run during this Planning turn.

## Backlog handoff

Recommended split candidates, whose names and creation remain the Host's Backlog decision:

1. A counts failure-reason bugfix preserves `UX-projects`, the existing neutral display and the shared request
   cadence. Its regression fails a real `OwedCountsStore.refresh` response inside the shared context and checks
   `Needs-you count unavailable: Database busy`. It also checks that a later successful read clears the reason
   and that no additional Projects counts request occurs. Error-state storage can remain internal to the store;
   the shell's neutral question mark and Attention consumers retain their current visible behavior.
2. A sidebar overflow-cue feature adds theme-token edge cues to the existing navigation. The top cue reflects
   content above, the bottom cue reflects content below, and neither appears without overflow. Cues are
   decorative; existing navigation and active-link scrolling remain accessible. Verification covers overflow,
   both scroll edges, resize/content changes and no overflow in the appropriate UI test harness.

These candidates have no behavioral dependency on one another. Their potential shared shell integration tests
still require file-level sequencing during Development. Neither candidate changes backend or typed API code.
No child proposal, ADR, production source or acceptance record was created by this Planning turn.
