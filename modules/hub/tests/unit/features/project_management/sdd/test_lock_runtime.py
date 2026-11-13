"""Runtime selection from a commit's own lock: group choice, rendering, classification and identity."""

import shutil
import sys
from pathlib import Path

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import lock_runtime
from app.features.project_management.sdd.lock_runtime import classify, select

FIXTURE = Path(__file__).parent / "fixtures/group-lock"
SEED = Path(__file__).parents[7] / "config/sdd-runtime"
REVISION = "a1ffedafd49ccd4bb6298bacacca1c25c0cf48ef"

pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="uv renders the lock")


def consumer(tmp_path, source=FIXTURE, edit=None) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    for name in ("pyproject.toml", "uv.lock"):
        text = (source / name).read_text()
        (root / name).write_text(edit(name, text) if edit else text)
    return root


@pytest.fixture(autouse=True)
def isolated_build(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOHUB_SDD_BUILD", str(tmp_path / "build"))


def test_group_selection_renders_only_the_devkit_group(tmp_path):
    selection = select(consumer(tmp_path))
    assert selection.group == "dev"
    assert {source.package for source in selection.git} >= {"devkit-spec", "devkit-agt", "devkit-advisory"}
    assert all(source.repository == "mjkimR/devkit" and source.revision == REVISION for source in selection.git)
    assert "iniconfig" not in selection.export
    assert all("--hash=sha256:" in line for line in selection.registry)


def test_main_dependencies_are_selected_without_a_group(tmp_path):
    selection = select(consumer(tmp_path, SEED))
    assert selection.group is None
    assert any(source.package == "devkit-spec" for source in selection.git)


def test_unrelated_lock_change_keeps_the_identity_and_group_change_does_not(tmp_path):
    base = select(consumer(tmp_path / "a")).identity

    def outside(name, text):
        return text.replace("2.1.0", "2.0.0")  # iniconfig: a main dependency outside the devkit group

    def inside(name, text):
        return text.replace("8.5.1", "8.5.0")  # click: inside the devkit group

    assert select(consumer(tmp_path / "b", edit=outside)).identity == base
    assert select(consumer(tmp_path / "c", edit=inside)).identity != base


def test_identity_covers_the_build_environment(tmp_path, monkeypatch):
    root = consumer(tmp_path)
    before = select(root).identity
    build = tmp_path / "other-build"
    build.mkdir()
    (build / "uv.lock").write_text("version = 1\n")
    monkeypatch.setenv("AUTOHUB_SDD_BUILD", str(build))
    assert select(root).identity != before


def _unlocked(root):
    with pytest.raises(ProjectError) as raised:
        select(root)
    assert raised.value.status == 422 and raised.value.code == "SDD_RUNTIME_UNLOCKED"


def test_repository_without_a_lock_is_refused(tmp_path):
    root = consumer(tmp_path)
    (root / "uv.lock").unlink()
    _unlocked(root)


def test_repository_whose_project_does_not_declare_devkit_spec_is_refused(tmp_path):
    def without(name, text):
        return text.replace('dev = ["devkit-spec", ', "dev = [") if name == "pyproject.toml" else text

    _unlocked(consumer(tmp_path, edit=without))


def test_symlinked_manifest_is_refused(tmp_path):
    root = consumer(tmp_path)
    (root / "pyproject.toml").unlink()
    (root / "pyproject.toml").symlink_to(FIXTURE / "pyproject.toml")
    with pytest.raises(ProjectError, match="uv.lock") as raised:
        select(root)
    assert raised.value.code == "SDD_RUNTIME_UNLOCKED"


def test_incompatible_python_is_refused_before_rendering(tmp_path, monkeypatch):
    major, minor = sys.version_info[:2]
    root = consumer(
        tmp_path,
        edit=lambda name, text: (
            text.replace('requires-python = ">=3.13,<3.14"', f'requires-python = ">={major}.{minor + 1}"')
            if name == "pyproject.toml"
            else text
        ),
    )
    monkeypatch.setattr(lock_runtime, "render", lambda *args: pytest.fail("rendered an incompatible project"))
    with pytest.raises(ProjectError) as raised:
        select(root)
    assert raised.value.code == "SDD_RUNTIME_PYTHON_UNSUPPORTED"


@pytest.mark.parametrize(
    "line",
    [
        "-e ./local",
        "--index-url https://example.com/simple",
        "pkg @ file:///tmp/pkg",
        "pkg @ https://example.com/pkg-1.0-py3-none-any.whl",
        f"pkg @ git+https://gitlab.com/o/r@{REVISION}",
        "pkg @ git+https://github.com/o/r@main",
        f"pkg @ git+https://github.com/o/r@{REVISION}#subdirectory=../escape",
        "pkg==1.0",  # registry requirement without hashes
    ],
)
def test_unsupported_sources_are_refused(line):
    with pytest.raises(ProjectError) as raised:
        classify(line + "\n")
    assert raised.value.code == "SDD_RUNTIME_SOURCE_UNSUPPORTED"


def test_classification_keeps_markers_and_hashes():
    digest = "a" * 64
    git, registry = classify(
        f"colorama==0.4.6 ; sys_platform == 'win32' \\\n    --hash=sha256:{digest}\n"
        f"devkit-spec @ git+https://github.com/mjkimR/devkit.git@{REVISION}#subdirectory=packages/devkit-spec\n"
    )
    assert registry == (f"colorama==0.4.6 ; sys_platform == 'win32' --hash=sha256:{digest}",)
    assert git[0].repository == "mjkimR/devkit" and git[0].subdirectory == "packages/devkit-spec"
