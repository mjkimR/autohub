import pytest
from app.features.execution.tasks.domains.jules.service import JulesSessionPayload

pytestmark = pytest.mark.unit


def payload(**overrides) -> JulesSessionPayload:
    return JulesSessionPayload(repository="owner/app", title="Hygiene", prompt="Tidy up.", **overrides)


def test_task_work_opens_a_pull_request_by_default_and_says_so():
    task = payload()
    assert (task.work_type, task.auto_create_pr) == ("task", True)
    assert task.session_prompt.startswith("Tidy up.\n\n")
    assert "open one pull request" in task.session_prompt


def test_a_report_stays_in_the_session_by_default_and_says_so():
    report = payload(work_type="report")
    assert report.auto_create_pr is False
    assert "final message" in report.session_prompt
    assert "Do not create branches" in report.session_prompt


def test_an_explicit_pull_request_mode_is_kept():
    assert payload(work_type="report", auto_create_pr=True).auto_create_pr is True
    assert payload(auto_create_pr=False).auto_create_pr is False


def test_unknown_work_types_are_rejected():
    with pytest.raises(ValueError):
        payload(work_type="audit")
