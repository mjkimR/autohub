# Sidebar overflow-cue evidence

Source inspected: `e1a50a8064597d65fd44906f1b65c01ad93c2425`.
Inherited from ~~`PROP-hub-ui-shell-polish`~~, retained at `d9cf2ae7ed792ecb8582c07d9f09979f544e26db`.
This records source/test inspection, not a browser walkthrough, test execution or deployed behavior.

`UX-app-shell` promises active-link scrolling but no overflow cue. `AppShell.svelte:154` renders an overflowing
navigation container without edge cues. `SidebarLink.svelte` scrolls the active link into view. Existing sidebar
tests do not establish overflow-state coverage.

The feature preserves that navigation behavior and adds decorative theme-token cues. Verification must cover
no overflow, top/middle/bottom positions, resize, System disclosure and administrative-link arrival. A real-layout
browser check in both themes and short desktop/narrow Menu states must establish visibility; mocked dimensions
alone cannot establish that outcome. Counts behavior remains with `PROP-owed-counts-error-reason`.
