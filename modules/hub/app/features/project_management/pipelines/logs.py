"""Bounded diagnostic excerpts from plain-text GitHub Actions job logs."""

import re

_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_TIMESTAMP = re.compile(r"^\ufeff?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\s?")
_SECRET = re.compile(
    r"(?i)(?:authorization:\s*bearer\s+|gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|(?:token|password|secret)\s*[=:]\s*)[^\s]+"
)
_EXIT = re.compile(r"^##\[error\]Process completed with exit code\b", re.IGNORECASE)
_DIAGNOSTIC = re.compile(
    r"##\[error\]|\b[\w.]+(?:Error|Exception):|\berror(?:\[[^\]]+\]| [A-Z]+\d+)?:"
    r"|\bfatal(?: error)?:|\bpanic:|^\s*(?:FAIL(?:ED)?\b|E\s{2,}\S)",
    re.IGNORECASE,
)


def failure_log_excerpt(text: str, max_chars: int) -> str | None:
    """Prefer an error and nearby context; never spend the budget on post-failure cleanup.

    Error recognition is best effort. An Actions exit annotation provides a
    fallback boundary for tools whose diagnostics do not match these patterns.
    Redact the complete normalized log before selecting or truncating anything.
    """
    if max_chars <= 0:
        return None
    normalized = "\n".join(_TIMESTAMP.sub("", line) for line in _ANSI.sub("", text).splitlines())
    lines = _SECRET.sub("[REDACTED]", normalized).splitlines()
    if not lines:
        return None
    exit_index = next((i for i, line in enumerate(lines) if _EXIT.search(line)), None)
    if exit_index is not None:
        lines = lines[: exit_index + 1]
    diagnostic = next(
        (
            i
            for i, line in enumerate(lines)
            if not line.startswith(("##[group]", "[command]")) and not _EXIT.search(line) and _DIAGNOSTIC.search(line)
        ),
        None,
    )
    if diagnostic is None:
        # A traceback without a recognizable exception still beats a cleanup tail.
        diagnostic = next((i for i, line in enumerate(lines) if "Traceback (most recent call last):" in line), None)
    if diagnostic is None:
        return "\n".join(lines)[-max_chars:] or None
    return _context_window(lines, diagnostic, max_chars)


def _context_window(lines: list[str], anchor: int, max_chars: int) -> str:
    error = lines[anchor]
    if len(error) >= max_chars:
        return error[:max_chars]
    before: list[str] = []
    after: list[str] = []
    remaining = max_chars - len(error)
    # Reserve most of the space for the stack/assertion preceding the error.
    before_budget = remaining * 2 // 3
    start = anchor - 1
    while start >= 0 and len(lines[start]) + 1 <= before_budget:
        before.append(lines[start])
        cost = len(lines[start]) + 1
        before_budget -= cost
        remaining -= cost
        start -= 1
    end = anchor + 1
    # A few following lines capture code frames without drifting into teardown.
    while end < min(len(lines), anchor + 5) and len(lines[end]) + 1 <= remaining:
        after.append(lines[end])
        remaining -= len(lines[end]) + 1
        end += 1
    while start >= 0 and len(lines[start]) + 1 <= remaining:
        before.append(lines[start])
        remaining -= len(lines[start]) + 1
        start -= 1
    return "\n".join([*reversed(before), error, *after])
