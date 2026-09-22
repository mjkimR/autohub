import pytest
from app.features.project_management.pipelines.logs import failure_log_excerpt


def test_canary_assertion_survives_timestamped_cleanup_noise():
    failure = [
        "##[group]Run python3 hello.py",
        "python3 hello.py",
        "##[endgroup]",
        "Traceback (most recent call last):",
        '  File "/home/runner/work/test-sandbox/hello.py", line 44, in <module>',
        '    assert absolute_difference(8, 3) == 5, "absolute_difference(8, 3) must equal 5"',
        "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
        "AssertionError: absolute_difference(8, 3) must equal 5",
        "##[error]Process completed with exit code 1.",
    ]
    lines = ["setup output"] * 100 + failure + ["[command]git config cleanup"] * 100
    log = "\n".join("2026-09-22T00:12:13.1610300Z " + line for line in lines)
    excerpt = failure_log_excerpt(log, 1_000)
    assert excerpt is not None
    assert excerpt is not None and len(excerpt) <= 1_000
    assert "Traceback (most recent call last):" in excerpt
    assert "assert absolute_difference(8, 3) == 5" in excerpt
    assert "AssertionError: absolute_difference(8, 3) must equal 5" in excerpt
    assert "git config cleanup" not in excerpt
    assert "2026-09-22T" not in excerpt


@pytest.mark.parametrize(
    "diagnostic",
    [
        "##[error]src/main.ts(8,3): Type 'string' is not assignable to type 'number'.",
        "src/main.ts(8,3): error TS2322: Type 'string' is not assignable to type 'number'.",
        "error[E0308]: mismatched types",
        "FAIL src/main.test.ts > returns an absolute difference",
        "fatal error: missing.h: No such file or directory",
        "panic: unexpected nil pointer",
    ],
)
def test_common_diagnostics_are_prioritized(diagnostic):
    log = "setup\n" * 100 + diagnostic + "\nsource context\n" + "cleanup\n" * 100
    excerpt = failure_log_excerpt(log, 150)
    assert excerpt is not None
    assert diagnostic in excerpt
    assert len(excerpt) <= 150


def test_unrecognized_failure_uses_output_before_exit_instead_of_teardown():
    log = "compiler output\n" * 100 + "expected 5 but received 11\n"
    log += "##[error]Process completed with exit code 1.\n" + "cleanup\n" * 100
    excerpt = failure_log_excerpt(log, 100)
    assert excerpt is not None
    assert "expected 5 but received 11" in excerpt
    assert "cleanup" not in excerpt
    assert len(excerpt) <= 100


def test_short_fallback_log_is_preserved_and_long_fallback_is_bounded():
    assert failure_log_excerpt("unknown tool output", 100) == "unknown tool output"
    excerpt = failure_log_excerpt("output\n" * 100 + "last line", 20)
    assert excerpt is not None
    assert excerpt.endswith("last line")


def test_redaction_happens_before_error_selection_and_truncation():
    secret = "s" * 300
    log = f"\x1b[31mAssertionError: token={secret} expected 5\x1b[0m\n" + "cleanup\n" * 100
    excerpt = failure_log_excerpt(log, 80)
    assert excerpt is not None
    assert "[REDACTED]" in excerpt
    assert "expected 5" in excerpt
    assert secret[:10] not in excerpt
    assert "\x1b" not in excerpt
    assert len(excerpt) <= 80


def test_long_traceback_keeps_the_exception_and_nearest_stack_frame():
    log = "Traceback (most recent call last):\n" + '  File "recursive.py", line 9\n' * 100
    log += '  File "hello.py", line 44\nAssertionError: expected 5\n'
    log += "##[error]Process completed with exit code 1.\n" + "cleanup\n" * 100
    excerpt = failure_log_excerpt(log, 150)
    assert excerpt is not None
    assert 'File "hello.py", line 44' in excerpt
    assert "AssertionError: expected 5" in excerpt
    assert len(excerpt) <= 150


def test_error_from_later_cleanup_does_not_replace_the_original_failure():
    log = "FAIL original test\n##[error]Process completed with exit code 1.\n"
    log += "##[error]cleanup failed\n"
    excerpt = failure_log_excerpt(log, 100)
    assert excerpt is not None
    assert "FAIL original test" in excerpt
    assert "cleanup failed" not in excerpt


@pytest.mark.parametrize("limit", [1, 10, 20, 100])
def test_single_long_error_line_respects_small_budgets(limit):
    excerpt = failure_log_excerpt("AssertionError: " + "x" * 1_000, limit)
    assert excerpt is not None
    assert len(excerpt) == limit


@pytest.mark.parametrize("text, limit", [("", 100), ("failure", 0), ("failure", -1)])
def test_empty_or_disabled_excerpt(text, limit):
    assert failure_log_excerpt(text, limit) is None
