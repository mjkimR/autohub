import pytest
from app.features.project_management import branches

pytestmark = pytest.mark.unit


def test_item_branches_are_dev_slugs_from_lowercased_keys():
    assert branches.item_branch("Schema") == "dev-schema"
    assert branches.item_branch("a" * 60) == "dev-" + "a" * 60  # the longest key still fits 64 characters
    assert branches.is_activity_branch("plan-login") and branches.is_activity_branch("dev-login_v2")
    assert not branches.is_activity_branch("feature/7")
    assert not branches.is_activity_branch("dev-Login")
    assert not branches.is_activity_branch("dev--x")  # the slug starts with a letter or digit
    assert not branches.is_activity_branch("dev-" + "a" * 61)


def test_units_map_to_their_activity_branch():
    assert branches.unit_branch("specs/2026-10/20261010-native") == "dev-native"
    assert branches.unit_branch("docs/proposals/PROP-login-rework/") == "plan-login-rework"
    assert branches.unit_branch("specs/2026-10/20261010-MyFeature") is None
    assert branches.unit_branch("src/thing") is None


def test_pull_request_head_must_be_the_unit_branch():
    assert branches.unit_branch_mismatch("specs/2026-10/20261010-native", "dev-native") is None
    message = branches.unit_branch_mismatch("specs/2026-10/20261010-native", "feature/7")
    assert message and "dev-native" in message and "feature/7" in message
    assert "does not name a unit slug" in str(branches.unit_branch_mismatch("specs/2026-10/20261010-X", "dev-x"))
