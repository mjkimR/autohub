"""Runtime selection from a commit's own lock: group choice, rendering, classification and identity."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.sdd import lock_runtime
from app.features.project_management.sdd.lock_runtime import classify, select

FIXTURE = Path(__file__).parent / "fixtures/group-lock"
PATH_FIXTURE = Path(__file__).parent / "fixtures/path-lock"
PATH_ONLY_FIXTURE = Path(__file__).parent / "fixtures/path-only-lock"
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


def checkout(tmp_path, source=PATH_FIXTURE) -> Path:
    """A whole fixture repository, path source trees included."""
    root = tmp_path / "repo"
    shutil.copytree(source, root)
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
    with pytest.raises(ProjectError, match=r"uv\.lock") as raised:
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
        "-e ../outside",
        "-e /abs/bundle",
        "../ext",
        "/abs/bundle",
        "./",
        "./tools/../escape",
        "./tools/my bundle",
        "./tools/plain ; sys_platform == 'linux'",
        "./tools/plain --hash=sha256:" + "a" * 64,
        "--index-url https://example.com/simple",
        "pkg @ file:///tmp/pkg",
        "pkg @ file:///tmp/pkg-1.0-py3-none-any.whl",
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
    git, registry, _ = classify(
        f"colorama==0.4.6 ; sys_platform == 'win32' \\\n    --hash=sha256:{digest}\n"
        f"devkit-spec @ git+https://github.com/mjkimR/devkit.git@{REVISION}#subdirectory=packages/devkit-spec\n"
    )
    assert registry == (f"colorama==0.4.6 ; sys_platform == 'win32' --hash=sha256:{digest}",)
    assert git[0].repository == "mjkimR/devkit" and git[0].subdirectory == "packages/devkit-spec"


def test_registry_package_from_another_index_is_refused(tmp_path):
    def mirrored(name, text):
        if name != "uv.lock":
            return text
        return text.replace(
            'name = "click"\nversion = "8.5.1"\nsource = { registry = "https://pypi.org/simple" }',
            'name = "click"\nversion = "8.5.1"\nsource = { registry = "https://mirror.example/simple" }',
        )

    with pytest.raises(ProjectError) as raised:
        select(consumer(tmp_path, edit=mirrored))
    assert raised.value.code == "SDD_RUNTIME_SOURCE_UNSUPPORTED"


def test_in_checkout_path_and_editable_sources_are_selected(tmp_path):
    selection = select(checkout(tmp_path / "p"))
    base = select(consumer(tmp_path / "g"))
    assert [(source.package, source.path) for source in selection.paths] == [
        ("my-bundle", "tools/my-bundle"),
        ("plain-bundle", "tools/plain"),
    ]
    assert selection.git == base.git and selection.registry == base.registry
    files = dict((name, data) for name, _, data in selection.paths[0].files)
    assert files["pyproject.toml"] == (PATH_FIXTURE / "tools/my-bundle/pyproject.toml").read_bytes()


def test_devkit_spec_may_itself_be_a_path_source(tmp_path):
    selection = select(checkout(tmp_path, PATH_ONLY_FIXTURE))
    assert selection.git == () and selection.registry == ()
    assert [source.package for source in selection.paths] == ["devkit-spec"]


def test_path_source_identity_is_the_same_across_checkout_directories(tmp_path):
    assert select(checkout(tmp_path / "a")).identity == select(checkout(tmp_path / "b")).identity


def test_path_source_content_and_executable_bit_change_the_identity(tmp_path):
    base = select(checkout(tmp_path / "a")).identity
    edited = checkout(tmp_path / "b")
    module = edited / "tools/my-bundle/src/my_bundle/__init__.py"
    module.write_bytes(module.read_bytes() + b" ")
    assert select(edited).identity != base
    executable = checkout(tmp_path / "c")
    os.chmod(executable / "tools/my-bundle/src/my_bundle/__init__.py", 0o755)
    assert select(executable).identity != base


def test_identity_without_path_sources_keeps_its_document(tmp_path):
    selection = select(consumer(tmp_path))
    document = {"build": lock_runtime.build_digest(), "export": selection.export, "python": selection.python}
    assert selection.paths == ()
    assert selection.identity == hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()


def _unsupported(root):
    with pytest.raises(ProjectError) as raised:
        select(root)
    assert raised.value.status == 422 and raised.value.code == "SDD_RUNTIME_SOURCE_UNSUPPORTED"
    return raised.value


def _symlinked_directory(root):
    real = root / "tools/real-bundle"
    (root / "tools/my-bundle").rename(real)
    (root / "tools/my-bundle").symlink_to(real)


def _symlink_inside(root):
    (root / "tools/my-bundle/src/link.py").symlink_to(root / "tools/plain/pyproject.toml")


def _symlinked_manifest(root):
    manifest = root / "tools/my-bundle/pyproject.toml"
    manifest.rename(root / "elsewhere.toml")
    manifest.symlink_to(root / "elsewhere.toml")


@pytest.mark.parametrize(
    "mutate",
    [
        _symlinked_directory,
        _symlink_inside,
        _symlinked_manifest,
        lambda root: shutil.rmtree(root / "tools/plain"),
        lambda root: (root / "tools/plain/pyproject.toml").unlink(),
        lambda root: os.mkfifo(root / "tools/plain/src/pipe"),
    ],
    ids=["symlinked-directory", "symlink-inside", "symlinked-manifest", "missing", "no-manifest", "fifo"],
)
def test_unsafe_path_source_trees_are_refused(tmp_path, mutate):
    root = checkout(tmp_path)
    mutate(root)
    _unsupported(root)


def test_path_source_outside_the_checkout_is_refused_before_reading_it(tmp_path, monkeypatch):
    root = checkout(tmp_path)
    lock = root / "uv.lock"
    lock.write_text(lock.read_text().replace('editable = "tools/my-bundle"', 'editable = "../my-bundle"'))
    monkeypatch.setattr(lock_runtime, "path_sources", lambda *args: pytest.fail("read a path source"))
    _unsupported(root)


def test_path_source_size_is_bounded(tmp_path, monkeypatch):
    root = checkout(tmp_path)
    monkeypatch.setattr(lock_runtime, "PATH_FILES_LIMIT", 3)  # the fixture's two sources hold four files
    assert "files" in _unsupported(root).detail
    monkeypatch.setattr(lock_runtime, "PATH_FILES_LIMIT", 10_000)
    monkeypatch.setattr(lock_runtime, "PATH_BYTES_LIMIT", 100)
    _unsupported(root)


def test_caches_and_git_metadata_are_not_captured(tmp_path):
    base = select(checkout(tmp_path / "a"))
    root = checkout(tmp_path / "b")
    for name in (".git/HEAD", ".venv/bin/python", "src/my_bundle/__pycache__/x.pyc"):
        (root / "tools/my-bundle" / name).parent.mkdir(parents=True, exist_ok=True)
        (root / "tools/my-bundle" / name).write_text("cache")
    assert select(root).identity == base.identity


def test_workspace_members_inside_the_checkout_install_like_path_sources(tmp_path):
    selection = select(checkout(tmp_path, Path(__file__).parent / "fixtures/workspace-lock"))
    assert [(source.package, source.path) for source in selection.paths] == [
        ("devkit-spec", "packages/devkit-spec"),
        ("member", "packages/member"),
    ]
