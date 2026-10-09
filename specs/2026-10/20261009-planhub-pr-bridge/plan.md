# Implementation plan

Extend the existing native adapter allowlist with provider/environment-scoped
checkout/project targets. Persist the resolved configuration in release snapshots.
New sdk_flow_pr_links records one flow owner and evidence snapshot per pipeline run.
The check task claims only an externally implemented paused run; it verifies trusted
checkout containment, HEAD, workflow binding and the CLI's actual integration gate.
The delivery task checks the recorded evidence again and uses the existing durable
RunResumeReceipt keyed by the flow attempt ID. The PR owner alone advances CI/merge.
A final resume guard locks and checks the flow row before the existing PR write.
Keep host-owned run pinning as an additive SDK 0.2 wire extension in this slice.
