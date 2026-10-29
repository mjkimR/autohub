"""Use real Git and installed sdd, including policy and version pins."""

import json
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd.services import STALE_LINT, SddService

from tests.integration.features.execution.flows import test_bridge

SPEC = test_bridge.SPEC
checkout = test_bridge.checkout

pytestmark = pytest.mark.integration


@asynccontextmanager
async def direct_publication(plan):
    """Git contract tests have no durable run; DB fencing is covered by test_plan_publication."""
    yield


def devkit_binary() -> str:
    return str(Path(os.environ["AUTOHUB_SDD_HOME"]) / ".venv/bin/devkit")


def run(root, *args):
    return subprocess.check_output(args, cwd=root, text=True, stderr=subprocess.DEVNULL).strip()


def commit(root, message):
    run(root, "git", "add", ".")
    identity = ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.com")
    run(root, "git", "-c", "core.hooksPath=/dev/null", *identity, "commit", "-qm", message)
    return run(root, "git", "rev-parse", "HEAD")


def extend_with_integration(root):
    """Append integrate and merge stages to the fixture workflow, rebind the spec and commit."""
    workflow = root / ".devkit/workflows/bridge-test.md"
    schema = json.loads(workflow.read_text().split("---")[1])
    common = {
        "artifacts": [],
        "skills": [],
        "role": "developer",
        "isolation": "none",
        "returns": [],
        "human_gate": False,
    }
    schema["stages"].extend(
        [
            {
                **common,
                "id": "fixture-integrate",
                "name": "Integrate",
                "entry": [],
                "exit": ["lint-ci-clean"],
            },
            {**common, "id": "fixture-merge", "name": "Merge", "entry": ["lint-ci-clean"], "exit": ["merged"]},
        ]
    )
    workflow.write_text("---\n" + json.dumps(schema) + "\n---\n")
    run(root, devkit_binary(), "workflow", "bind", "--unit", SPEC, "--workflow", str(workflow.relative_to(root)))
    return commit(root, "Extend fixture")


def fresh_clone(root, tmp_path):
    fresh = (tmp_path / "fresh").resolve()
    subprocess.run(["git", "clone", "--quiet", str(root), str(fresh)], check=True)
    return fresh


def commit_stale_receipt(root, bundle, asset_id, suffix):
    """Commit a receipt whose record of one ``bundle`` ``asset_id`` file no longer matches what the runtime deploys."""
    manifest = root / ".devkit/installation.json"
    receipt = json.loads(manifest.read_text())
    asset = next(item for item in receipt["assets"] if item["bundle"] == bundle and item["id"] == asset_id)
    path = next(item for item in asset["paths"] if item.endswith(suffix))
    receipt["files"][path]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(receipt, indent=2) + "\n")
    return commit(root, f"Stale receipt for {asset_id}"), manifest.read_text()


async def test_real_cli_reads_gate_and_rejects_changed_version(checkout):
    root, head = checkout
    service = SddService()
    evidence = await service.evaluate(root, SPEC, head, head, None, False)
    assert evidence["current"]["stage"]["human_gate"]
    assert not evidence["integrated"]
    assert evidence["warnings"] == []
    assert evidence["snapshot"]["policy"]["approvals"]["dev-integration"]["policy"] == "ask"
    with pytest.raises(ProjectError, match="version"):
        await service.evaluate(root, SPEC, head, head, {**evidence["snapshot"], "cli_version": "unsupported"}, False)
    with pytest.raises(ProjectError, match="workflow or policy"):
        await service.evaluate(root, SPEC, head, head, {**evidence["snapshot"], "workflow_hash": "changed"}, False)


async def test_real_cli_final_lint_and_no_change_integration(checkout):
    root, _ = checkout
    head = extend_with_integration(root)
    evidence = await SddService().evaluate(root, SPEC, head, head, None, True)
    assert evidence["integrated"]
    assert evidence["current"]["stage"]["id"] == "fixture-merge"
    assert evidence["head_sha"] == evidence["base_sha"] == head


async def test_fresh_checkout_restores_recorded_release_without_network(checkout, tmp_path):
    root, _ = checkout
    fresh = fresh_clone(root, tmp_path)
    manifest = fresh / ".devkit/installation.json"
    original = manifest.read_bytes()
    assert not (fresh / ".devkit/managed").exists()
    head = run(fresh, "git", "rev-parse", "HEAD")
    result = await SddService().evaluate(fresh, SPEC, head, head, None, False)
    assert result["current"]["stage"]["human_gate"]
    assert result["reports"][0]["kind"] == "final-report"
    assert result["reports"][0]["summary"] == "Fixture verified"
    assert manifest.read_bytes() == original
    assert (fresh / ".devkit/managed/spec/workflows/sdd-spec-feature.md").is_file()
    assert not run(fresh, "git", "diff", "--name-only")


async def test_stale_receipt_is_evaluated_best_effort_and_reported(checkout, tmp_path):
    root, _ = checkout
    fresh = fresh_clone(root, tmp_path)
    head, committed = commit_stale_receipt(fresh, "spec", "sdd-spec-feature", ".md")
    result = await SddService().evaluate(fresh, SPEC, head, head, None, False)
    assert [item["code"] for item in result["warnings"]] == ["RECEIPT_STALE"]
    assert result["current"]["stage"]["human_gate"]
    assert result["reports"][0]["summary"] == "Fixture verified"
    assert (fresh / ".devkit/managed/spec/workflows/sdd-spec-feature.md").is_file()
    # The snapshot digests the committed receipt, not the one regenerated inside the disposable checkout.
    config = (fresh / ".devkit/config.toml").read_text()
    assert result["snapshot"]["configuration_digest"] == request_digest({"config": config, "receipt": committed})
    assert (fresh / ".devkit/installation.json").read_text() != committed
    assert run(fresh, "git", "rev-parse", "HEAD") == head


@pytest.mark.parametrize(
    ("bundle", "asset_id", "suffix", "integrated"),
    [("spec", "sdd-spec-feature", ".md", True), ("docs", "spec-format", "rule.py", False)],
)
async def test_stale_receipt_integration_depends_on_recorded_rules(
    checkout, tmp_path, bundle, asset_id, suffix, integrated
):
    root, _ = checkout
    extend_with_integration(root)
    fresh = fresh_clone(root, tmp_path)
    base = run(fresh, "git", "rev-parse", "HEAD")
    head, _ = commit_stale_receipt(fresh, bundle, asset_id, suffix)  # the PR change the final lint evaluates
    evidence = await SddService().evaluate(fresh, SPEC, head, base, None, True)
    assert [item["code"] for item in evidence["warnings"]] == ["RECEIPT_STALE"]
    assert evidence["integrated"] is integrated
    if integrated:
        assert evidence["lint_diagnostic"] is None
        assert evidence["current"]["stage"]["id"] == "fixture-merge"
    else:
        # The committed tree still records the rule, and its regenerated copy no longer matches: no silent pass.
        assert evidence["lint_diagnostic"] == STALE_LINT
        assert evidence["current"]["stage"]["id"] == "fixture-integrate"


async def test_devkit_authors_answer_and_return_and_invalidates_approval(checkout):
    from app.features.project_management.sdd.decisions import prepare_record
    from app.features.project_management.sdd.services import cli

    root, _ = checkout
    operation = {
        "id": "a-fixed-receipt",
        "request": "gate:dev-integration",
        "action": "accept",
        "actor": "user:fixture",
    }
    record = await prepare_record(root, SPEC, operation, cli)
    assert record["file"].startswith("decisions/")
    assert "autohub-decision:a-fixed-receipt" in record["content"]
    current = await cli(root, "workflow", "next", "--unit", SPEC)
    assert current["complete"]
    await prepare_record(
        root, SPEC, {"id": "return-receipt", "return_to": "bridge-approval", "actor": "user:fixture"}, cli
    )
    current = await cli(root, "workflow", "next", "--unit", SPEC)
    assert current["requests"][0]["id"] == "gate:dev-integration"
    assert current["requests"][0]["answer"] == "given"  # Hub passes it as --given, never as a record
    assert not current["complete"]


async def test_repository_python_rule_cannot_read_host_secret_or_use_network(checkout, tmp_path, monkeypatch):
    """Repository Python reaches devkit through a project override of a rule; it runs only inside the sandbox."""
    from app.features.project_management.sdd.checkout import command

    root, base = checkout
    secret = tmp_path / "server-secret.txt"
    secret.write_text("must-not-leak")
    monkeypatch.setenv("SDD_TEST_SECRET", "must-not-leak")
    run(root, devkit_binary(), "override", "create", "docs:spec-format")
    rule = root / ".devkit/overrides/docs/rules/spec_format/rule.py"
    report = root / "probe.json"
    rule.write_text(
        "import json, os, socket\nfrom pathlib import Path\n"
        f"try:\n data = Path({str(secret)!r}).read_text()\nexcept OSError:\n data = 'denied'\n"
        "try:\n socket.create_connection(('127.0.0.1', 9), timeout=1)\n network = 'allowed'\n"
        "except OSError as exc:\n network = exc.errno\n"
        f"Path({str(report)!r}).write_text(json.dumps("
        "{'file': data, 'env': os.environ.get('SDD_TEST_SECRET'), 'network': network}))\n" + rule.read_text()
    )
    run(root, devkit_binary(), "sync")  # the receipt records the edited override
    commit(root, "Probe override")
    await command("devkit", "rules", "check", "--ci", "--base", base, "--format", "json", cwd=root, allow_failure=True)
    probe = json.loads(report.read_text())
    assert probe["file"] == "denied"
    assert probe["env"] is None
    assert probe["network"] in (1, 13, 101)  # EPERM/EACCES, or ENETUNREACH in a fresh Linux network namespace


async def test_accepted_handoff_authorizes_only_the_selected_definition(checkout):
    from app.features.project_management.sdd.decisions import prepare_record
    from app.features.project_management.sdd.services import cli

    root, _ = checkout
    path = root / ".devkit/workflows/bridge-test.md"
    definition = json.loads(path.read_text().split("---")[1])
    successor = {
        **definition,
        "id": "delivery-successor",
        "title": "Successor",
        "stages": [{**definition["stages"][-1], "id": "successor-approval"}],
    }
    target = root / ".devkit/workflows/successor.md"
    target.write_text("---\n" + json.dumps(successor) + "\n---\n")
    definition["next"] = [{"workflow": "delivery-successor", "when": [], "recommended": True}]
    path.write_text("---\n" + json.dumps(definition) + "\n---\n")
    from app.features.project_management.sdd.checkout import command

    await command("devkit", "workflow", "bind", "--unit", SPEC, "--workflow", "bridge-test", cwd=root)
    await prepare_record(
        root, SPEC, {"id": "g3", "request": "gate:dev-integration", "action": "accept", "actor": "user:fixture"}, cli
    )
    before = await SddService().evaluate(root, SPEC, "head", "base", None, False)
    assert before["current"]["requests"][0]["id"] == "handoff"
    record = await prepare_record(
        root,
        SPEC,
        {
            "id": "handoff",
            "request": "handoff",
            "action": "accept",
            "value": "delivery-successor",
            "actor": "user:fixture",
        },
        cli,
    )
    await cli(root, "workflow", "handoff", "--unit", SPEC)
    with pytest.raises(ProjectError, match="workflow or policy"):
        await SddService().evaluate(root, SPEC, "head", "base", before["snapshot"], False)
    snapshot = {**before["snapshot"], "authorized_workflows": [record["authorized_workflow"]]}
    after = await SddService().evaluate(root, SPEC, "head", "base", snapshot, False)
    assert after["current"]["requests"][0]["id"] == "gate:dev-integration"
    assert after["current"]["stage"]["id"] == "successor-approval"


def worker_envelope(root, *args):
    return run(
        root, devkit_binary(), "workflow", "envelope", "worker", "--unit", SPEC, "--stage", "bridge-check", *args
    )


async def test_worker_question_waits_until_an_answer_envelope_exists(checkout, tmp_path):
    root, _ = checkout
    questions = tmp_path / "questions.yaml"
    questions.write_text(
        "- id: q1\n  title: Storage format\n  prompt: Which format should settings use?\n"
        "  options:\n    - { id: a, description: Keep TOML, recommended: true }\n"
        "    - { id: b, description: Switch to JSON }\n"
    )
    worker_envelope(root, "--summary", "Needs a decision", "--questions-file", str(questions))
    head = commit(root, "Worker asks")
    waiting = await SddService().evaluate(root, SPEC, head, head, None, True)
    assert waiting["hold"]["pending_questions"] == [
        {"file": "envelopes/worker-01.yaml", "id": "q1", "title": "Storage format"}
    ]
    assert not waiting["hold"]["blocked"] and not waiting["integrated"]
    request = waiting["current"]["requests"][0]
    assert (request["id"], request["answer"], request["kind"]) == ("question:worker-01.q1", "envelope", "choose")
    assert request["target"]["name"] == "worker-01.yaml#q1"
    assert waiting["current"]["gate"]["held"]  # --given dev-integration passes nothing while a question waits
    answers = tmp_path / "answers.yaml"
    answers.write_text("- question: q1\n  choice: a\n  decision: Keep TOML\n")
    run(
        root,
        devkit_binary(),
        "workflow",
        "envelope",
        "answer",
        "--unit",
        SPEC,
        "--answers-to",
        "worker-01.yaml",
        "--answers-file",
        str(answers),
        "--summary",
        "q1 decided",
    )
    head = commit(root, "Operator answered")
    answered = await SddService().evaluate(root, SPEC, head, head, None, False)
    assert answered["hold"]["pending_questions"] == [] and not answered["hold"]["blocked"]
    assert answered["current"]["requests"][0]["id"] == "gate:dev-integration"


async def test_unresolved_problem_blocks_until_a_resolution_envelope(checkout, tmp_path):
    root, _ = checkout
    worker_envelope(root, "--summary", "Build stopped", "--problem", "Fixture broke", "--recovery", "Repair it")
    head = commit(root, "Worker failed")
    blocked = await SddService().evaluate(root, SPEC, head, head, None, True)
    assert blocked["hold"]["blocked"] and not blocked["integrated"]
    assert blocked["hold"]["problems"][0]["file"] == "envelopes/worker-01.yaml"
    assert blocked["hold"]["problems"][0]["cause"] == "Fixture broke"
    assert blocked["hold"]["problems"][0]["recovery"] == "Repair it"
    run(
        root,
        devkit_binary(),
        "workflow",
        "envelope",
        "resolution",
        "--unit",
        SPEC,
        "--resolves",
        "worker-01.yaml",
        "--summary",
        "Fixture repaired",
    )
    head = commit(root, "Resolved")
    resolved = await SddService().evaluate(root, SPEC, head, head, None, False)
    assert not resolved["hold"]["blocked"] and resolved["hold"]["problems"] == []


async def test_runtime_status_starts_devkit_inside_the_sandbox(checkout):
    status = await SddService().runtime_status()
    assert status["ok"], status
    assert status["isolation"] in ("sandbox-exec", "bubblewrap")
    assert "devkit" in status["detail"]
    assert set(status["revisions"]) >= {"devkit-spec", "devkit-agt"}


PROPOSAL = "docs/proposals/PROP-demo"


def reviewing_proposal(root, automatic=False):
    """A proposal past plan-intent and in review, committed on the fixture's branch."""
    from app.features.project_management.sdd import units

    run(root, "git", "checkout", "-q", "-b", "plan-demo")
    if automatic:
        config = root / ".devkit/config.toml"
        config.write_text(config.read_text() + '\n[workflow.approvals]\nplan-intent = "auto"\nplan-accept = "auto"\n')
        run(root, devkit_binary(), "sync")
    run(root, devkit_binary(), "spec", "proposal", "new", "demo", "--title", "Demo", "--task-kind", "feature")
    if not automatic:
        run(
            root,
            devkit_binary(),
            "workflow",
            "answer",
            "--unit",
            PROPOSAL,
            "--request",
            "gate:plan-intent",
            "--action",
            "accept",
            "--by",
            "user:fixture",
        )
    units.set_status(root, PROPOSAL, "draft", "reviewing")
    # Current proposal workflows require a feedback sweep before asking plan-accept.
    run(
        root,
        devkit_binary(),
        "workflow",
        "envelope",
        "new",
        "--kind",
        "feedback",
        "--unit",
        PROPOSAL,
        "--status",
        "completed",
        "--summary",
        "No feedback remains",
        "--check",
        "swept=PASS",
    )
    return commit(root, "Proposal in review")


async def test_owning_base_policy_does_not_inherit_head_delegation(checkout):
    root, base = checkout
    head = reviewing_proposal(root, automatic=True)
    value = await SddService().evaluate(root, PROPOSAL, head, base, None, False)
    assert value["current"]["complete"] and not value["current"]["requests"]
    assert value["snapshot"]["policy"]["approvals"]["plan-accept"]["policy"] == "auto"
    assert value["base_policy"]["approvals"]["plan-accept"]["policy"] == "ask"
    assert not list((root / ".devkit/transient").glob("hub-base-*"))


@pytest.mark.parametrize("agent_accepted", [False, True])
async def test_policy_acceptance_authors_a_decision_commit_even_after_agent_acceptance(
    checkout, tmp_path, monkeypatch, agent_accepted
):
    from app.features.project_management.sdd.plan_decisions import record_plan_decision

    root, _ = checkout
    head = reviewing_proposal(root, automatic=True)
    if agent_accepted:
        run(root, devkit_binary(), "spec", "proposal", "accept", "demo", "--by", "policy")
        head = commit(root, "Agent accepted under policy")
    bare = bare_remote(root, tmp_path, head, monkeypatch)
    evidence = await SddService().evaluate(root, PROPOSAL, head, head, None, False)
    plan = await record_plan_decision(
        SddService(),
        "owner/app",
        PROPOSAL,
        pull_at(head),
        "token",
        decision="accept_plan",
        actor="policy:auto",
        authority="policy",
        note="Delegated",
        snapshot=evidence["snapshot"],
        expected_digest=evidence["evidence_digest"],
        request_id="auto-accept",
        publication=direct_publication,
    )
    assert plan["authority"] == "policy" and plan["commit_sha"] != head
    assert run(bare, "git", "rev-parse", "refs/heads/plan-demo") == plan["commit_sha"]
    assert "status: accepted" in run(bare, "git", "show", f"{plan['commit_sha']}:{PROPOSAL}/proposal.md")
    assert "Autohub-Decision: auto-accept" in run(bare, "git", "log", "-1", "--format=%B", plan["commit_sha"])


async def test_auto_plan_intent_starts_without_a_decision_filename(checkout, tmp_path, monkeypatch):
    from app.features.project_management.sdd.policy import planning_intent

    root, _ = checkout
    reviewing_proposal(root, automatic=True)
    from app.features.project_management.sdd.units import set_status

    set_status(root, PROPOSAL, "reviewing", "draft")
    head = commit(root, "Backlog draft with delegated intent")
    bare_remote(root, tmp_path, head, monkeypatch)
    assert not list((root / PROPOSAL / "decisions").glob("*gate-plan-intent*"))
    assert await planning_intent("owner/app", head, "token", PROPOSAL)


def bare_remote(root, tmp_path, head, monkeypatch):
    """A bare clone standing in for GitHub: plan-demo at ``head``; pushes go there instead of github.com."""
    from app.features.project_management.sdd import checkout as checkout_module

    bare = (tmp_path / "remote.git").resolve()
    subprocess.run(["git", "clone", "--quiet", "--bare", str(root), str(bare)], check=True)
    run(bare, "git", "update-ref", "refs/heads/plan-demo", head)
    monkeypatch.setattr(checkout_module, "remote_url", lambda repository: str(bare))
    return bare


def pull_at(head):
    return {"head": {"sha": head, "ref": "plan-demo"}, "base": {"sha": head, "ref": "main"}}


async def test_acceptance_is_one_commit_on_the_confirmed_head_pushed_under_a_lease(checkout, tmp_path, monkeypatch):
    from app.features.project_management.sdd.plan_decisions import record_plan_decision

    root, _ = checkout
    head = reviewing_proposal(root)
    bare = bare_remote(root, tmp_path, head, monkeypatch)
    before = await SddService().evaluate(root, PROPOSAL, head, head, None, False)
    assert before["unit_status"] == "reviewing"
    assert before["current"]["requests"][0]["id"] == "gate:plan-accept"
    plan = await record_plan_decision(
        SddService(),
        "owner/app",
        PROPOSAL,
        pull_at(head),
        "token",
        decision="accept_plan",
        actor="user:fixture",
        note="Go ahead",
        snapshot=before["snapshot"],
        expected_digest=before["evidence_digest"],
        request_id="r1",
        publication=direct_publication,
    )
    assert run(bare, "git", "rev-parse", "refs/heads/plan-demo") == plan["commit_sha"]
    assert run(bare, "git", "log", "-1", "--format=%P", plan["commit_sha"]) == head  # parent: the confirmed head
    assert run(bare, "git", "log", "-1", "--format=%an <%ae>", plan["commit_sha"]) == (
        "AutoHub <autohub@users.noreply.github.com>"
    )
    message = run(bare, "git", "log", "-1", "--format=%B", plan["commit_sha"])
    assert message.startswith("Accept proposal PROP-demo") and "Decided-by: user:fixture" in message
    changed = run(bare, "git", "diff", "--name-only", head, plan["commit_sha"]).splitlines()
    assert sorted(changed) == [f"{PROPOSAL}/decisions/02-gate-plan-accept.yaml", f"{PROPOSAL}/proposal.md"]
    decision = run(bare, "git", "show", f"{plan['commit_sha']}:{PROPOSAL}/decisions/02-gate-plan-accept.yaml")
    assert "by: user" in decision and "Decided-by: user:fixture" in decision
    # The fixture checkout did not move; evaluate the pushed commit from a fresh clone of the remote.
    verify = (tmp_path / "verify").resolve()
    subprocess.run(["git", "clone", "--quiet", "--branch", "plan-demo", str(bare), str(verify)], check=True)
    after = await SddService().evaluate(verify, PROPOSAL, plan["commit_sha"], plan["commit_sha"], None, False)
    assert after["unit_status"] == "accepted" and after["current"]["complete"] and not after["current"]["requests"]
    # The remote moved on: the same confirmed head no longer holds, so a second decision is refused.
    with pytest.raises(ProjectError, match="head changed"):
        await record_plan_decision(
            SddService(),
            "owner/app",
            PROPOSAL,
            pull_at(head),
            "token",
            decision="accept_plan",
            actor="user:fixture",
            note="",
            snapshot=before["snapshot"],
            expected_digest=before["evidence_digest"],
            request_id="r2",
            publication=direct_publication,
        )


@pytest.mark.parametrize("question_count", [1, 11])
async def test_rejection_changes_status_only_and_closes_open_questions(checkout, tmp_path, monkeypatch, question_count):
    from app.features.project_management.sdd.plan_decisions import record_plan_decision

    root, _ = checkout
    reviewing_proposal(root)
    questions = tmp_path / "questions.yaml"
    questions.write_text(
        "".join(
            f"- id: q{i}\n  title: Storage format\n  prompt: Which format?\n  options:\n    - {{ id: a, description: TOML }}\n"
            for i in range(1, question_count + 1)
        )
    )
    run(
        root,
        devkit_binary(),
        "workflow",
        "envelope",
        "worker",
        "--unit",
        PROPOSAL,
        "--stage",
        "direction-handoff",
        "--summary",
        "Needs a decision",
        "--questions-file",
        str(questions),
    )
    head = commit(root, "Worker asks")
    bare = bare_remote(root, tmp_path, head, monkeypatch)
    before = await SddService().evaluate(root, PROPOSAL, head, head, None, False)
    assert before["hold"]["pending_questions"] and before["current"]["gate"]["held"]
    plan = await record_plan_decision(
        SddService(),
        "owner/app",
        PROPOSAL,
        pull_at(head),
        "token",
        decision="reject_plan",
        actor="user:fixture",
        note="Too broad; split it",
        snapshot=before["snapshot"],
        expected_digest=before["evidence_digest"],
        request_id="r3",
        publication=direct_publication,
    )
    message = run(bare, "git", "log", "-1", "--format=%B", plan["commit_sha"])
    assert message.startswith("Reject proposal PROP-demo: Too broad; split it")
    changed = run(bare, "git", "diff", "--name-only", head, plan["commit_sha"]).splitlines()
    assert sorted(changed) == [f"{PROPOSAL}/envelopes/answer-01.yaml", f"{PROPOSAL}/proposal.md"]
    verify = (tmp_path / "verify").resolve()
    subprocess.run(["git", "clone", "--quiet", "--branch", "plan-demo", str(bare), str(verify)], check=True)
    after = await SddService().evaluate(verify, PROPOSAL, plan["commit_sha"], plan["commit_sha"], None, False)
    assert after["unit_status"] == "rejected"
    assert after["hold"]["pending_questions"] == [] and not after["hold"]["blocked"]
    assert not after["current"]["requests"]  # a rejected proposal is never asked for acceptance again


async def test_acceptance_refuses_another_proposals_branch_without_publishing(checkout, tmp_path, monkeypatch):
    from app.features.project_management.sdd.plan_decisions import record_plan_decision

    root, _ = checkout
    head = reviewing_proposal(root)
    bare = bare_remote(root, tmp_path, head, monkeypatch)
    pull = pull_at(head)
    pull["head"]["ref"] = "plan-other"
    before = await SddService().evaluate(root, PROPOSAL, head, head, None, False)
    with pytest.raises(ProjectError, match="own Planning branch"):
        await record_plan_decision(
            SddService(),
            "owner/app",
            PROPOSAL,
            pull,
            "token",
            decision="accept_plan",
            actor="user:fixture",
            note="",
            snapshot=before["snapshot"],
            expected_digest=before["evidence_digest"],
            request_id="wrong-branch",
            publication=direct_publication,
        )
    assert run(bare, "git", "rev-parse", "refs/heads/plan-demo") == head
    assert "status: reviewing" in run(bare, "git", "show", f"{head}:{PROPOSAL}/proposal.md")


async def test_activity_branch_is_started_once_from_the_base(checkout, tmp_path, monkeypatch):
    from app.features.project_management.sdd import units
    from app.features.project_management.sdd.activities import start_branch

    root, _ = checkout
    run(root, devkit_binary(), "spec", "proposal", "new", "demo", "--title", "Demo", "--task-kind", "feature")
    base = commit(root, "Draft proposal")
    bare = (tmp_path / "remote.git").resolve()
    subprocess.run(["git", "clone", "--quiet", "--bare", str(root), str(bare)], check=True)
    from app.features.project_management.sdd import checkout as checkout_module

    monkeypatch.setattr(checkout_module, "remote_url", lambda repository: str(bare))

    def reviewing(checkout_root):
        units.set_status(checkout_root, PROPOSAL, "draft", "reviewing")

    sha = await start_branch("owner/app", base, "plan-demo", "token", ("Start Planning of PROP-demo", "x"), reviewing)
    assert run(bare, "git", "rev-parse", "refs/heads/plan-demo") == sha
    assert run(bare, "git", "log", "-1", "--format=%P", sha) == base
    assert run(bare, "git", "diff", "--name-only", base, sha) == f"{PROPOSAL}/proposal.md"
    with pytest.raises(ProjectError, match="already exists"):
        await start_branch("owner/app", base, "plan-demo", "token", ("again", "x"), None)


async def test_handoff_first_run_follows_the_new_spec_after_the_handoff(checkout):
    root, _ = checkout
    reviewing_proposal(root)
    run(
        root,
        devkit_binary(),
        "spec",
        "proposal",
        "accept",
        "demo",
        "--by",
        "user",
    )
    head = commit(root, "Accepted")
    before = await SddService().evaluate(root, PROPOSAL, head, head, {"handoff_pending": True}, False)
    assert before["unit_status"] == "accepted" and before["current"]["complete"]
    assert "rebound" not in before
    run(root, "git", "checkout", "-q", "-b", "dev-demo")
    run(root, devkit_binary(), "spec", "proposal", "handoff", "demo")
    head = commit(root, "Handoff")
    pinned = {**before["snapshot"], "handoff_pending": True}
    after = await SddService().evaluate(root, PROPOSAL, head, head, pinned, False)
    assert after["rebound"] and after["snapshot"]["handoff_from"] == PROPOSAL
    assert after["snapshot"]["spec_dir"].startswith("specs/") and after["snapshot"]["spec_dir"].endswith("-demo")
    assert after["snapshot"]["workflow_id"] == "sdd-spec-feature"
    assert after["current"]["stage"]["id"] == "specify"  # plan-intent carried over from the proposal
