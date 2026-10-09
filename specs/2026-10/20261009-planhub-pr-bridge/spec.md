# Planhub SDK delivery and specrig/PR bridge

Status: completed (implementation and local verification; uncommitted). Workbench F3, paired with planhub SPEC-autohub-application-delivery.

The host supports optional expected release identity/digest on submission so an
activation race cannot execute a different definition. Existing SDK 0.2 requests
retain their original digest and behavior.

Native allowlisted targets verify actual checkout HEAD and `specrig workflow show/next`
JSON, retain review/final-report/reconcile evidence digest, and claim an existing paused
PipelineRun for one FlowRun. Scoped approval permits replay-safe resume through the
existing PR owner's receipt; a final transaction guard checks flow revision/lease and
PR head/revision. The bridge observes paused/blocked/failure/terminal states without
creating a second PR execution or owning CI/merge. Cancel fences that owner; it cannot
promise external agent termination or roll back effects.

Verify DB claims, same-attempt resume recovery, changed head/evidence rejection,
namespace/checkout restrictions, real Git/CLI checks and typed state projection.
Regenerate UI API schema, verify migration roundtrip, and run full backend/static checks.
No deployed GitHub writes, new PR creation, F4 coordination or operating deployment.
