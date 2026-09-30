"""Parse explicit, attempt-bound questions from already authenticated agent replies."""

import json
import re

from app.features.project_management.pipeline_runs.dispatch import CODEX_MENTION

_QUESTION = re.compile(r"<!-- autohub-question (\{[^\n]*\}) -->")
_MAX_QUESTION_CHARS = 8000
# JSON can encode one Unicode code point as a 12-character surrogate pair.
# Bound the wire text separately, allowing space for metadata and surrounding prose.
_MAX_REPLY_CHARS = 12 * _MAX_QUESTION_CHARS + 16000


def parse_question(body: str, correlation_marker: str, head_sha: str) -> str | None:
    match = _QUESTION.search(body[:_MAX_REPLY_CHARS])
    if match is None:
        return None
    try:
        value = json.loads(match.group(1))
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict) or value.get("attempt") != correlation_marker or value.get("head") != head_sha:
        return None
    question = value.get("question")
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= _MAX_QUESTION_CHARS:
        return None
    if CODEX_MENTION.search(question) or "<!--" in question:
        return None
    return question.strip()
