# Verification evidence

Retain evidence needed to distinguish local implementation from production
behavior. These reports record past checks; neither proves the current source or
serving revision. See [delivery status](../operations/deployment-status.md) for
rollout gaps and the owning behavior references.

| Record | Why it remains |
| --- | --- |
| [Production verification, recorded baseline 2026-10-02](2026-10/20261002-production-verification/report.md) | Live GitHub/provider checks, deployment identities, manual-intervention exceptions and coverage limits |
| [devkit 0.1.6 local verification, 2026-11-05](2026-11/20261105-delivery-verification/report.md) | Reviewed toolchain identity, primary/follow-up check scopes and compatibility evidence awaiting production rollout |

Superseded design discussions, resolved code/tool reviews and older local test
chronology are available in Git history. Current behavior belongs in its owning
reference. Add a material only when its source identity, observation or uncertainty
is needed for a current decision or compatibility/deployment claim.
