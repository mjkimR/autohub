import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import plan_decisions, units

pytestmark = pytest.mark.unit
UNIT = "docs/proposals/PROP-demo"
ANCHOR = "---\nid: PROP-demo\ntitle: Demo\nstatus: reviewing                     # draft | reviewing | accepted | rejected\ncreated_at: 2026-10-16\n---\n# Demo\n\nstatus: not frontmatter\n"


def test_units_tell_specs_from_proposals():
    assert units.unit_anchor("specs/2026-10/20261010-native") == "spec.md"
    assert units.unit_anchor(UNIT) == "proposal.md" and units.is_proposal(UNIT)
    assert units.unit_anchor("src/x") is None
    assert units.proposal_slug(UNIT) == "demo"
    with pytest.raises(ProjectError, match="proposal units"):
        units.proposal_slug("specs/2026-10/20261010-native")


def test_status_is_read_and_rewritten_in_the_frontmatter_only(tmp_path):
    (tmp_path / UNIT).mkdir(parents=True)
    (tmp_path / UNIT / "proposal.md").write_text(ANCHOR, encoding="utf-8")
    assert units.read_status(tmp_path, UNIT) == "reviewing"
    with pytest.raises(ProjectError, match="is reviewing, not draft"):
        units.set_status(tmp_path, UNIT, "draft", "reviewing")
    units.set_status(tmp_path, UNIT, "reviewing", "rejected")
    text = (tmp_path / UNIT / "proposal.md").read_text(encoding="utf-8")
    assert "status: rejected                     # draft | reviewing | accepted | rejected" in text
    assert text.endswith("status: not frontmatter\n")  # the body is untouched
    assert units.read_status(tmp_path, UNIT) == "rejected"
    assert units.read_status(tmp_path, "docs/proposals/PROP-missing") is None


def test_commit_identity_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("AUTOHUB_SDD_COMMIT_IDENTITY", raising=False)
    assert plan_decisions.commit_identity() == ("AutoHub", "autohub@users.noreply.github.com")
    monkeypatch.setenv("AUTOHUB_SDD_COMMIT_IDENTITY", "Hub Bot <bot@example.com>")
    assert plan_decisions.commit_identity() == ("Hub Bot", "bot@example.com")
    monkeypatch.setenv("AUTOHUB_SDD_COMMIT_IDENTITY", "nobody")
    with pytest.raises(ProjectError, match="Name <email>"):
        plan_decisions.commit_identity()


def test_commit_messages_keep_the_reason_first_and_name_the_decider():
    title, body = plan_decisions.commit_message("accept_plan", "demo", "user:mj", "", "a" * 40)
    assert title == "Accept proposal PROP-demo" and body == "Decided-by: user:mj\nHead: " + "a" * 40
    title, body = plan_decisions.commit_message("reject_plan", "demo", "user:mj", "Too broad.\nSplit it.", "a" * 40)
    assert title == "Reject proposal PROP-demo: Too broad."
    assert body.startswith("Too broad.\nSplit it.\n\nDecided-by: user:mj")


def test_closure_answers_cover_every_open_question_per_worker_file():
    pending = [
        {"file": "envelopes/worker-01.yaml", "id": "q1", "title": "A"},
        {"file": "envelopes/worker-01.yaml", "id": "q2", "title": "B"},
        {"file": "envelopes/worker-02.yaml", "id": "q1", "title": "C"},
        {"file": "envelopes/../etc", "id": "x", "title": "unsafe"},
    ]
    answers = plan_decisions.closure_answers(pending, 'Not now: "scope" too wide\nmore')
    assert set(answers) == {"worker-01.yaml", "worker-02.yaml"}
    assert answers["worker-01.yaml"].count("choice: null") == 2
    assert 'decision: "Planning ended by rejection: Not now: \\"scope\\" too wide"' in answers["worker-01.yaml"]
