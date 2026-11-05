"""Compatibility checks reject independent drift without Git, network or installed viewers."""

import json
import runpy
import shutil
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[5]
checker = runpy.run_path(str(ROOT / "scripts/check-devkit.py"))
check = checker["check"]
PinsError = checker["DevkitPinsError"]


@pytest.fixture
def project(tmp_path):
    for profile in checker["PROFILES"]:
        for name in ("pyproject.toml", "uv.lock"):
            target = tmp_path / profile / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / profile / name, target)
    for name in (
        "package-lock.json",
        "vendor/devkit-viewer.source.json",
        "vendor/devkit-viewer-0.1.0.tgz",
    ):
        target = tmp_path / "modules/hub-ui" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "modules/hub-ui" / name, target)
    return tmp_path


def test_reviewed_three_profiles_and_viewer_match(project):
    revision, version = check(project)
    assert len(revision) == 40 and version


@pytest.mark.parametrize("profile", checker["PROFILES"])
@pytest.mark.parametrize("name", ["pyproject.toml", "uv.lock"])
def test_one_profiles_git_pin_cannot_drift(project, profile, name):
    revision, _ = check(project)
    path = project / profile / name
    path.write_text(path.read_text().replace(revision, "f" * 40))
    with pytest.raises(PinsError) as refused:
        check(project)
    assert refused.value.code == "DEVKIT_PINS_INVALID"


def test_transitive_package_version_cannot_drift(project):
    _, version = check(project)
    path = project / "config/sdd-runtime/uv.lock"
    path.write_text(
        path.read_text().replace(
            f'name = "devkit-core"\nversion = "{version}"', 'name = "devkit-core"\nversion = "0.0.0"'
        )
    )
    with pytest.raises(PinsError):
        check(project)


def test_catalog_git_pin_cannot_drift_independently(project):
    revision, _ = check(project)
    path = project / "uv.lock"
    text = path.read_text()
    start = text.index('\nname = "devkit-catalog"\n')
    end = text.index("\n[[package]]", start)
    path.write_text(text[:start] + text[start:end].replace(revision, "f" * 40) + text[end:])
    with pytest.raises(PinsError, match="resolved devkit-catalog Git source"):
        check(project)


@pytest.mark.parametrize("profile", checker["PROFILES"][1:])
def test_catalog_does_not_belong_in_isolated_sdd_runtime(project, profile):
    path = project / "uv.lock"
    text = path.read_text()
    start = text.index('\nname = "devkit-catalog"\n')
    end = text.index("\n[[package]]", start)
    catalog = "\n[[package]]" + text[start:end]
    runtime_lock = project / profile / "uv.lock"
    runtime_lock.write_text(runtime_lock.read_text() + catalog)
    assert any(package["name"] == "devkit-catalog" for package in tomllib.loads(runtime_lock.read_text())["package"])
    with pytest.raises(PinsError, match="package inventory"):
        check(project)


def test_override_cannot_pin_a_different_toolchain(project):
    revision, _ = check(project)
    path = project / "pyproject.toml"
    path.write_text(path.read_text().replace(f"devkit@{revision}#", f"devkit@{'f' * 40}#", 1))
    with pytest.raises(PinsError):
        check(project)


@pytest.mark.parametrize("field,value", [("commit", "f" * 40), ("version", "0.0.0"), ("sha256", "0" * 64)])
def test_stale_viewer_source_receipt_is_rejected(project, field, value):
    path = project / "modules/hub-ui/vendor/devkit-viewer.source.json"
    source = json.loads(path.read_text())
    source[field] = value
    path.write_text(json.dumps(source))
    with pytest.raises(PinsError):
        check(project)


def test_changed_viewer_tarball_is_rejected(project):
    path = project / "modules/hub-ui/vendor/devkit-viewer-0.1.0.tgz"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(PinsError):
        check(project)


def test_stale_npm_integrity_is_rejected(project):
    path = project / "modules/hub-ui/package-lock.json"
    lock = json.loads(path.read_text())
    lock["packages"]["node_modules/devkit-viewer"]["integrity"] = "sha512-stale"
    path.write_text(json.dumps(lock))
    with pytest.raises(PinsError):
        check(project)
