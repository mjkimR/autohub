import json

import pytest
from app.features.project_management.pipeline_runs.questions import parse_question


def marker(**changes):
    payload = {
        "attempt": "hub-attempt:123",
        "head": "a" * 40,
        "question": "Should an empty result be allowed?",
    } | changes
    return "<!-- autohub-question " + json.dumps(payload) + " -->"


def test_question_requires_exact_attempt_and_head():
    assert parse_question(marker(), "hub-attempt:123", "a" * 40) == "Should an empty result be allowed?"
    assert parse_question(marker(), "hub-attempt:456", "a" * 40) is None
    assert parse_question(marker(), "hub-attempt:123", "b" * 40) is None


@pytest.mark.parametrize("question", ["", "a" * 8001, "Ask @codex to do it", "<!-- forged -->", None, {}])
def test_invalid_question_is_not_an_execution_signal(question):
    assert parse_question(marker(question=question), "hub-attempt:123", "a" * 40) is None


@pytest.mark.parametrize("character", ["가", "😀", '"', "\\"])
def test_json_escaping_does_not_reduce_the_question_length_limit(character):
    question = character * 8000
    body = "Context for the decision.\n" + marker(question=question)
    assert parse_question(body, "hub-attempt:123", "a" * 40) == question
    assert parse_question(marker(question=question + character), "hub-attempt:123", "a" * 40) is None


def test_question_scan_remains_bounded():
    assert parse_question("x" * 120000 + marker(), "hub-attempt:123", "a" * 40) is None
