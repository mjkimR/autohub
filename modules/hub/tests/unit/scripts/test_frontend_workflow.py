"""Execute contributor recipes with isolated tools and files, without Git or network effects."""

import os
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[5]

TOOL = r"""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

name = Path(sys.argv[0]).name
args = sys.argv[1:]
trace = Path(os.environ["WORKFLOW_TRACE"])

def record(phase):
    with trace.open("a") as stream:
        stream.write(phase + "\n")
    if os.environ.get("WORKFLOW_FAIL") == phase:
        sys.exit(17)

if name == "uv":
    if args[0] == "sync":
        assert args == ["sync", "--no-active", "--locked", "--all-packages"]
        record("python:locked")
    elif "devkit" in args and args[args.index("devkit") + 1] == "sync":
        assert args[-1] == "--locked"
        record("assets:locked")
    else:
        assert args[:6] == ["run", "--no-active", "--no-sync", "devkit", "run", "--"]
        sys.exit(subprocess.call(args[6:]))
elif name == "npm":
    assert args[0] == "--prefix"
    package = Path(args[1])
    args = args[2:]
    if args == ["install"]:
        record("frontend:install")
        (package / "node_modules").mkdir()
    else:
        assert args[0] == "run"
        command = json.loads((package / "package.json").read_text())["scripts"][args[1]]
        extra = args[2:]
        if extra:
            assert extra[0] == "--"
            command += " " + shlex.join(extra[1:])
        sys.exit(subprocess.call(command, shell=True, cwd=package))
elif name == "prettier":
    record("format:write" if "--write" in args else "format:check")
    fixture = Path("format-input.ts")
    if "--write" in args:
        fixture.write_text("formatted\n")
    elif fixture.read_text() != "formatted\n":
        sys.exit(1)
elif name == "eslint":
    record("eslint:fix" if "--fix" in args else "eslint:check")
    fixture = Path("lint-input.ts")
    if "--fix" in args:
        fixture.write_text("linted\n")
    elif fixture.read_text() != "linted\n":
        sys.exit(1)
"""


@pytest.fixture
def checkout(tmp_path):
    for source in ("justfile", "scripts/lint.sh", "scripts/_lib.sh", "modules/hub-ui/package.json"):
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, target)
    (tmp_path / "scripts/check-backend.sh").write_text(
        '#!/usr/bin/env bash\nprintf "backend:%s\\n" "$*" >> "$WORKFLOW_TRACE"\n'
    )
    ui = tmp_path / "modules/hub-ui"
    (ui / "format-input.ts").write_text("unformatted\n")
    (ui / "lint-input.ts").write_text("unlinted\n")
    tools = tmp_path / "bin"
    tools.mkdir()
    for name in ("uv", "npm", "prettier", "eslint"):
        executable = tools / name
        executable.write_text(f"#!{sys.executable}\n" + TOOL)
        executable.chmod(0o755)
    nvm = tmp_path / "nvm"
    nvm.mkdir()
    (nvm / "nvm.sh").write_text('nvm() { printf "node:activate\\n" >> "$WORKFLOW_TRACE"; }\n')
    env = {**os.environ, "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}", "NVM_DIR": str(nvm)}
    env["WORKFLOW_TRACE"] = str(tmp_path / "trace")
    env.pop("WORKFLOW_FAIL", None)
    return tmp_path, env


def run(checkout, *args, fail=None):
    path, env = checkout
    if fail:
        env = {**env, "WORKFLOW_FAIL": fail}
    return subprocess.run(args, cwd=path, env=env, capture_output=True, text=True, check=False)


def trace(checkout):
    path = checkout[0] / "trace"
    return path.read_text().splitlines() if path.exists() else []


def setup_command():
    return shlex.split(tomllib.loads((ROOT / ".devkit/config.toml").read_text())["worktree"]["setup"])


def test_configured_worktree_setup_initializes_python_assets_and_frontend(checkout):
    result = run(checkout, *setup_command())
    assert result.returncode == 0, result.stderr
    assert trace(checkout) == ["python:locked", "assets:locked", "node:activate", "frontend:install"]
    assert (checkout[0] / "modules/hub-ui/node_modules").is_dir()


@pytest.mark.parametrize("phase", ["python:locked", "assets:locked", "frontend:install"])
def test_configured_setup_stops_when_a_phase_fails(checkout, phase):
    result = run(checkout, *setup_command(), fail=phase)
    assert result.returncode != 0
    assert trace(checkout)[-1] == phase
    assert not (checkout[0] / "modules/hub-ui/node_modules").exists()


@pytest.mark.parametrize("module", ["hub-ui", "frontend", "ui"])
def test_fixing_recipe_formats_before_enabling_eslint_fixes(checkout, module):
    result = run(checkout, "just", "lint", module)
    assert result.returncode == 0, result.stdout + result.stderr
    assert trace(checkout) == ["node:activate", "format:write", "format:check", "eslint:fix"]
    ui = checkout[0] / "modules/hub-ui"
    assert (ui / "format-input.ts").read_text() == "formatted\n"
    assert (ui / "lint-input.ts").read_text() == "linted\n"


def test_read_only_recipe_reports_formatting_without_changing_input(checkout):
    ui = checkout[0] / "modules/hub-ui"
    before = {p.name: p.read_bytes() for p in ui.glob("*.ts")}
    result = run(checkout, "just", "lint-check", "hub-ui")
    assert result.returncode != 0
    assert trace(checkout) == ["node:activate", "format:check"]
    assert {p.name: p.read_bytes() for p in ui.glob("*.ts")} == before


def test_read_only_recipe_checks_eslint_without_fixing(checkout):
    ui = checkout[0] / "modules/hub-ui"
    (ui / "format-input.ts").write_text("formatted\n")
    result = run(checkout, "just", "lint-check", "hub-ui")
    assert result.returncode != 0
    assert trace(checkout) == ["node:activate", "format:check", "eslint:check"]
    assert (ui / "lint-input.ts").read_text() == "unlinted\n"


@pytest.mark.parametrize("phase", ["format:write", "eslint:fix"])
def test_fixing_recipe_propagates_frontend_failures(checkout, phase):
    result = run(checkout, "just", "lint", "hub-ui", fail=phase)
    assert result.returncode != 0
    assert trace(checkout)[-1] == phase


def test_backend_selection_never_runs_frontend_tools(checkout):
    result = run(checkout, "just", "lint", "backend")
    assert result.returncode == 0
    assert trace(checkout) == ["backend:--fix modules/hub"]
