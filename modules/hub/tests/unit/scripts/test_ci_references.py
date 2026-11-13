"""Run static CI checks on disposable workflows without executing their commands."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[5]
CHECK = ROOT / "scripts/check-ci-references.py"


@pytest.fixture
def checkout(tmp_path):
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "justfile").write_text('available +args="":\n    @touch EXECUTED\nalias short := available\n')
    return tmp_path


def workflow(root, run, *, step_dir=None, job_dir=None, workflow_dir=None, **fields):
    step = {"run": run, **fields}
    if step_dir is not None:
        step["working-directory"] = step_dir
    job = {"steps": [step]}
    if job_dir is not None:
        job["defaults"] = {"run": {"working-directory": job_dir}}
    data = {"jobs": {"checks": job}}
    if workflow_dir is not None:
        data["defaults"] = {"run": {"working-directory": workflow_dir}}
    (root / ".github/workflows/check.yml").write_text(yaml.safe_dump(data))


def run(root):
    return subprocess.run([sys.executable, str(CHECK), "--root", str(root)], capture_output=True, text=True)


def test_missing_recipe_fails_with_workflow_job_and_step(checkout):
    workflow(checkout, "just removed-recipe")
    result = run(checkout)
    assert result.returncode == 1
    assert "check.yml:checks:step 1" in result.stderr
    assert "removed-recipe" in result.stderr


def test_existing_recipes_and_aliases_are_introspected_without_running(checkout):
    workflow(checkout, "just available\njust short")
    result = run(checkout)
    assert result.returncode == 0, result.stderr
    assert "checked=2" in result.stdout
    assert not (checkout / "EXECUTED").exists()


@pytest.mark.parametrize("arg", ["config/deleted", '"config/deleted file"', "--manifest=config/deleted"])
def test_missing_literal_config_fails(checkout, arg):
    workflow(checkout, f"just available {arg}")
    result = run(checkout)
    assert result.returncode == 1
    assert "missing config path" in result.stderr


@pytest.mark.parametrize("kind", ["workflow", "job", "step"])
def test_existing_quoted_config_resolves_inherited_working_directory(checkout, kind):
    path = checkout / "module/config/manifest with spaces"
    path.parent.mkdir(parents=True)
    path.touch()
    kwargs = {f"{kind}_dir": "module"}
    workflow(checkout, 'just short "./config/manifest with spaces"', **kwargs)
    result = run(checkout)
    assert result.returncode == 0, result.stderr


def test_step_directory_overrides_job_and_workflow_defaults(checkout):
    path = checkout / "step/config/manifest"
    path.parent.mkdir(parents=True)
    path.touch()
    workflow(checkout, "just available config/manifest", step_dir="step", job_dir="job", workflow_dir="workflow")
    assert run(checkout).returncode == 0


def test_comments_prose_and_multiline_continuations(checkout):
    path = checkout / "config/manifest"
    path.parent.mkdir()
    path.touch()
    workflow(
        checkout,
        '# just removed config/missing\necho "just removed config/missing"\nprintf "config/missing"\njust available \\\n  config/manifest # config/missing',
        name="just removed config/missing",
    )
    result = run(checkout)
    assert result.returncode == 0, result.stderr
    assert "checked=1" in result.stdout


def test_simple_nonjust_config_argument_is_checked(checkout):
    workflow(checkout, "python tool.py --manifest=config/missing")
    result = run(checkout)
    assert result.returncode == 1
    assert "missing config path" in result.stderr


def test_dynamic_and_compound_shell_are_visible_unverified_skips(checkout):
    workflow(
        checkout,
        "just $RECIPE config/${NAME}\njust removed && echo done\njust available config/${{ inputs.manifest }}\njust --working-directory module removed",
    )
    result = run(checkout)
    assert result.returncode == 0, result.stderr
    assert "skipped=4" in result.stdout
    assert "unverified" in result.stdout


def test_dynamic_working_directory_skips_step(checkout):
    workflow(checkout, "just removed", step_dir="${{ matrix.directory }}")
    result = run(checkout)
    assert result.returncode == 0, result.stderr
    assert "skipped=1" in result.stdout


def test_invalid_yaml_fails_clearly(checkout):
    (checkout / ".github/workflows/check.yml").write_text("jobs: [")
    result = run(checkout)
    assert result.returncode == 1
    assert "CI_REFERENCES_INVALID" in result.stderr


def test_invalid_shell_quoting_fails_clearly(checkout):
    workflow(checkout, "just 'unfinished")
    result = run(checkout)
    assert result.returncode == 1
    assert "CI_REFERENCES_INVALID" in result.stderr


def test_current_repository_workflows_pass_without_modification():
    result = run(ROOT)
    assert result.returncode == 0, result.stderr
    assert "errors=0" in result.stdout


def test_backend_lint_hook_runs_checker_and_propagates_failure_read_only(tmp_path):
    tools = tmp_path / "bin"
    tools.mkdir()
    trace = tmp_path / "trace"
    (tools / "just").write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$CI_TRACE"\n[ "$1" != check-ci-references ] || exit 17\n'
    )
    (tools / "uv").write_text("#!/bin/sh\nexit 0\n")
    for tool in tools.iterdir():
        tool.chmod(0o755)
    before = (ROOT / "scripts/check-backend.sh").read_bytes()
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/check-backend.sh")],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}", "CI_TRACE": str(trace)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 17
    assert trace.read_text().splitlines() == ["check-devkit", "check-ci-references"]
    assert (ROOT / "scripts/check-backend.sh").read_bytes() == before
