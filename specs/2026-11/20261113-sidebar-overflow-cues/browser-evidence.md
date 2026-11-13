# Sidebar browser layout evidence

Real headless Google Chrome ran the authored `AppShell`, `SidebarNavViewport`, navigation groups/links and production layout.css through an ignored local Vite harness. The harness replaced page state and API responses with controlled local fixtures; no backend, authentication, provider or deployed-service verification is claimed. The source in this worktree is committed with this record.

The final matrix passed 31 recorded cases. Chrome used actual CSS layout and scrolling; no DOM dimensions were mocked. The inspected light desktop and dark Menu screenshots show readable active links, visible directional shadows in reserved gutters and reachable controls. Harness, results and screenshots remain ignored under `.devkit/tmp/review-probes/browser/`; integration cleanup removes them.

| Viewport and theme | Nav top/bottom | Active top/bottom after alignment | Logout bottom | Page scroll |
| --- | --- | --- | --- | --- |
| 1280×480 light | 96 / 323 | 279 / 319 | 442 | 0 |
| 1280×480 dark | 96 / 323 | 279 / 319 | 442 | 0 |
| 390×640 light Menu | 168 / 482 | 438 / 478 | 601 | 0 |
| 390×640 dark Menu | 168 / 482 | 438 / 478 | 601 | 0 |
| 390×640 lower System destination reveal | 168 / 482 | 438 / 478 | 601 | 0 |

Each of the four overflow cases verified top-only-hidden, middle and bottom positions against scrollHeight/clientHeight/scrollTop. All visible cues had pointer-events:none and theme-derived gradients. System expansion changed the measured content without a user scroll. Actual Tab navigation reached System configs with its computed 3px focus ring and at least 3px clearance inside navigation. Manual System collapse survived Menu close/reopen.

At 1280×1100 the list fit (clientHeight=scrollHeight=847); neither cue appeared. With ResizeObserver disabled in Chrome, Menu reveal, System content mutation, resize from 390×640 to 390×500 and scrolling to bottom still updated cues, and session controls stayed within the 500px viewport.

Reproduction command: activate the repository Node version, then run `node .devkit/tmp/review-probes/browser/verify.mjs` while its isolated Vite server listens on 127.0.0.1:5197. The harness is a disposable verification aid, not a maintained e2e suite. Unit integration tests retain deterministic edge, lifecycle, fallback, late-admin and reveal regressions.
