import pytest
from app.features.execution.dispatchers.services import _operator_message
from app.features.project_management.pipelines.github import GitHubObservationError
from app.features.project_management.projects.services import ProjectError

pytestmark = pytest.mark.unit


def test_errors_written_for_an_operator_are_kept_on_the_job():
    assert _operator_message(ProjectError(409, "Pipeline run has no active attempt")) == (
        "ProjectError: Pipeline run has no active attempt"
    )
    assert _operator_message(GitHubObservationError("GitHub merge returned HTTP 500", 500)) == (
        "GitHubObservationError: GitHub merge returned HTTP 500"
    )
    assert len(_operator_message(ProjectError(502, "x" * 5000)) or "") == 1000


def test_any_other_error_stays_in_the_logs():
    assert _operator_message(RuntimeError("postgresql://user:secret@host/db refused")) is None
    assert _operator_message(KeyError("token")) is None
