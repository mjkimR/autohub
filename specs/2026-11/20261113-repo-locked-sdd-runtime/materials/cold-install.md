# Cold install of a lock-derived SDD runtime

Measured on 2026-11-13 for `SPEC-repo-locked-sdd-runtime` AC-18.

## Setup

- Image: the serving image built from this branch (`docker/hub.Dockerfile`), run locally with Docker Desktop.
- Shape: `--cpus=1 --memory=1g`, matching the Cloud Run service (cpu=1, 1Gi).
- Isolation: bubblewrap. Docker Desktop's default seccomp/AppArmor profile refused `bwrap` mounting `/proc`, so
  the run used `--privileged`. The serving host must allow the same namespaces; the host probe verifies it.
- Input: the root `pyproject.toml` and `uv.lock` of the g-scavenger-crew pilot repository (group `dev`: 10 GitHub
  Git sources, 20 hashed registry wheels), with an empty cache and an empty uv cache.
- Credential: a GitHub token with read access to the locked private sources, used only by the Hub-process fetch.

## Results

| Run | Elapsed | Retained entry | Transient staging peak |
| --- | --- | --- | --- |
| 1 | 11.3 s | 29 MiB | not sampled |
| 2 | 11.4 s | 29 MiB | not sampled |
| 3 | 11.1 s | 29 MiB | 153 MiB |
| 4 (after review round 1 hardening: sandboxed wheel install) | 12.4 s | 29 MiB | not sampled |
| 5 (after review round 2: late sandboxes write only `.venv`) | 13.8 s | 29 MiB | not sampled |

The entry's `pin.json` lists the bundles `advisory`, `app-uiux-improve`, `authoring`, `cli-tool`,
`command-design`, `deep-research`, `design-explore`, `devkit`, `docs`, `g-foundation`, `git-commits`, `harness`,
`maintenance`, `response-style` and `spec`; the three bundles that server profiles lacked are present.

## Consequences

- The default `AUTOHUB_SDD_CACHE_BYTES` is 256 MiB: about eight retained entries, leaving room on a 1 GiB
  instance for one concurrent install's transient peak and evaluation checkouts.
- An install fits well inside one dispatcher interval, but a first readiness request still receives
  `SDD_RUNTIME_PREPARING` and must be retried; Cloud Run CPU throttling between requests can lengthen it.
