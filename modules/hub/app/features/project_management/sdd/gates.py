"""The devkit-spec gate Hub decides itself; every other request is relayed as the workflow defines it.

``dev-integration`` is the integration approval of the strategy layer (workbench docs/strategy-layer/01-master-flow.md
section 3). Its answer channel is ``given``: Hub passes ``--given dev-integration`` on the recorded basis and never
authors a decision record for it. ``plan-intent`` and ``plan-accept`` are record-channel gates answered through the
generic workflow-request controls; ``question:*`` requests are answered by an answer envelope, never by Hub.

The name is devkit-spec's: devkit itself is gate-neutral and only uses ``integration`` as a generic example in its
configuration template and docs. Hub builds on devkit-spec, so it follows devkit-spec's name, not devkit's example.
"""

INTEGRATION_GATE = "dev-integration"
INTEGRATION_REQUEST = f"gate:{INTEGRATION_GATE}"
# Accepting a proposal: a record-channel gate Hub writes itself as a deterministic commit (01 section 4.2).
PLAN_ACCEPT_GATE = "plan-accept"
PLAN_ACCEPT_REQUEST = f"gate:{PLAN_ACCEPT_GATE}"
