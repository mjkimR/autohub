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
