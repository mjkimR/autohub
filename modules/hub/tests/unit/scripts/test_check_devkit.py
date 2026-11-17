"""Compatibility checks reject independent Python pin drift without Git or network."""

import runpy
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[5]
checker = runpy.run_path(str(ROOT / "scripts/check-devkit.py"))
check = checker["check"]
PinsError = checker["DevkitPinsError"]


@pytest.fixture
def project(tmp_path):
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(ROOT / name, tmp_path / name)
    return tmp_path


def test_reviewed_root_toolchain_matches_without_viewer_files(project):
    revision, version = check(project)
    assert len(revision) == 40 and version


@pytest.mark.parametrize("name", ["pyproject.toml", "uv.lock"])
def test_root_git_pin_cannot_drift(project, name):
    revision, _ = check(project)
    path = project / name
    path.write_text(path.read_text().replace(revision, "f" * 40))
    with pytest.raises(PinsError) as refused:
        check(project)
    assert refused.value.code == "DEVKIT_PINS_INVALID"


def set_lock_version(project, name, version):
    path = project / "uv.lock"
    text = path.read_text()
    start = text.index(f'\nname = "{name}"\nversion = "') + len(f'\nname = "{name}"\nversion = "')
    end = text.index('"', start)
    path.write_text(text[:start] + version + text[end:])


def test_selective_package_versions_share_the_release_series(project):
    _, release = check(project)
    set_lock_version(project, "devkit-core", release.rsplit(".", 1)[0] + ".0")
    assert check(project)[1] == release


@pytest.mark.parametrize("drifted", ["0.0.0", "0.1.99", "0.2.0", "0.1.7rc1"])
def test_transitive_package_version_cannot_drift(project, drifted):
    set_lock_version(project, "devkit-core", drifted)
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


def test_missing_development_package_is_rejected(project):
    path = project / "uv.lock"
    text = path.read_text()
    start = text.index('\nname = "devkit-catalog"\n')
    end = text.index("\n[[package]]", start)
    package_start = text.rfind("\n[[package]]", 0, start)
    path.write_text(text[:package_start] + text[end:])
    with pytest.raises(PinsError, match="package inventory"):
        check(project)


def test_override_cannot_pin_a_different_toolchain(project):
    revision, _ = check(project)
    path = project / "pyproject.toml"
    path.write_text(path.read_text().replace(f"devkit@{revision}#", f"devkit@{'f' * 40}#", 1))
    with pytest.raises(PinsError):
        check(project)
