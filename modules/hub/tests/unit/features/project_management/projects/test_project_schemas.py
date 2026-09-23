from uuid import uuid4

import pytest
from app.features.project_management.projects.schemas import (
    ProjectObservationPayload,
    ProjectPatch,
    ProjectUpdate,
    ProjectWrite,
)
from app.features.project_management.projects.templates import TEMPLATE_PROFILES, list_templates
from pydantic import ValidationError

pytestmark = pytest.mark.unit

VERIFICATION = {"workflow": "ci.yml", "required_jobs": ["lint", "test"]}


def make_write(**overrides) -> dict:
    return {
        "name": "My application",
        "github": {
            "repository": "Owner/App",
            "github_connector_id": str(uuid4()),
            "verification": VERIFICATION,
        },
        **overrides,
    }


class TestProjectWrite:
    def test_repository_is_normalized_before_the_pattern_is_applied(self):
        data = make_write()
        data["github"]["repository"] = "  Owner/App  "
        project = ProjectWrite.model_validate(data)
        assert project.github is not None
        assert project.github.repository == "owner/app"

    @pytest.mark.parametrize("repository", ["owner", "owner/", "/app", "owner/app/extra", "-owner/app", "own er/app"])
    def test_malformed_repositories_are_rejected(self, repository):
        with pytest.raises(ValidationError):
            data = make_write()
            data["github"]["repository"] = repository
            ProjectWrite.model_validate(data)

    @pytest.mark.parametrize("name", ["", "   "])
    def test_blank_names_are_rejected(self, name):
        with pytest.raises(ValidationError):
            ProjectWrite.model_validate(make_write(name=name))

    def test_unknown_fields_are_rejected_so_stale_payloads_fail_loudly(self):
        with pytest.raises(ValidationError):
            ProjectWrite.model_validate(make_write(revision=2))

    def test_unknown_template_ids_are_rejected(self):
        with pytest.raises(ValidationError):
            ProjectWrite.model_validate(make_write(template_id="python-poetry"))

    def test_observation_config_carries_the_saved_connection(self):
        data = ProjectWrite.model_validate(make_write())
        assert data.github is not None
        config = data.observation_config([7, 9])
        assert (config.repository, config.pull_numbers) == ("owner/app", [7, 9])
        assert config.github_connector_id == data.github.github_connector_id
        assert config.verification == data.github.verification

    def test_automation_defaults_preserve_the_existing_unattended_workflow(self):
        project = ProjectWrite.model_validate(make_write())
        assert project.github is not None
        assert project.github.automation.model_dump() == {
            "auto_merge": True,
            "merge_method": "squash",
            "auto_fix_ci": True,
            "auto_fix_conflicts": True,
            "auto_enroll_on_trigger": True,
            "auto_enroll_sessions": True,
            "dispatch_interval_seconds": 60,
            "max_in_flight_runs": None,
        }

    @pytest.mark.parametrize("interval", [29, 3601])
    def test_dispatch_interval_has_safe_bounds(self, interval):
        data = make_write()
        data["github"]["automation"] = {"dispatch_interval_seconds": interval}
        with pytest.raises(ValidationError):
            ProjectWrite.model_validate(data)

    def test_project_can_be_created_without_any_provider_connection(self):
        project = ProjectWrite.model_validate({"name": "Planning"})
        assert project.github is None
        with pytest.raises(ValueError, match="GitHub connection"):
            project.observation_config([7])

    def test_updates_require_the_revision_the_editor_started_from(self):
        with pytest.raises(ValidationError):
            ProjectUpdate.model_validate(make_write())
        assert ProjectUpdate.model_validate(make_write(expected_revision=3)).expected_revision == 3


class TestProjectPatch:
    def current(self) -> ProjectWrite:
        data = make_write()
        data["github"]["automation"] = {"auto_merge": False, "merge_method": "rebase", "max_in_flight_runs": 3}
        return ProjectWrite.model_validate(data)

    def test_omitted_fields_keep_their_current_values(self):
        current = self.current()
        merged = ProjectPatch.model_validate({"expected_revision": 2, "name": "Renamed"}).apply_to(current)
        assert merged.name == "Renamed"
        assert merged.expected_revision == 2
        assert merged.github == current.github

    def test_nested_objects_merge_and_lists_replace(self):
        patch = ProjectPatch.model_validate(
            {
                "expected_revision": 2,
                "github": {"automation": {"auto_fix_ci": False}, "verification": {"required_jobs": ["build"]}},
            }
        )
        merged = patch.apply_to(self.current())
        assert merged.github is not None
        assert merged.github.automation.auto_fix_ci is False
        assert merged.github.automation.auto_merge is False
        assert merged.github.automation.merge_method == "rebase"
        assert merged.github.verification.workflow == "ci.yml"
        assert merged.github.verification.required_jobs == ["build"]

    def test_explicit_null_clears_nullable_fields(self):
        patch = ProjectPatch.model_validate(
            {"expected_revision": 2, "github": {"automation": {"max_in_flight_runs": None}}}
        )
        merged = patch.apply_to(self.current())
        assert merged.github is not None and merged.github.automation.max_in_flight_runs is None
        assert (
            ProjectPatch.model_validate({"expected_revision": 2, "github": None}).apply_to(self.current()).github
            is None
        )

    def test_merged_result_is_validated_as_a_whole(self):
        with pytest.raises(ValidationError):
            ProjectPatch.model_validate(
                {"expected_revision": 2, "github": {"automation": {"auto_merge": None}}}
            ).apply_to(self.current())
        partial = ProjectPatch.model_validate({"expected_revision": 2, "github": {"repository": "owner/app"}})
        with pytest.raises(ValidationError):
            partial.apply_to(ProjectWrite.model_validate({"name": "Unconnected"}))

    def test_legacy_flat_fields_nest_under_github(self):
        patch = ProjectPatch.model_validate({"expected_revision": 2, "automation": {"auto_merge": True}})
        assert patch.github is not None and patch.github.automation is not None
        merged = patch.apply_to(self.current())
        assert merged.github is not None and merged.github.automation.auto_merge is True

    def test_revision_is_required(self):
        with pytest.raises(ValidationError):
            ProjectPatch.model_validate({"name": "No revision"})


class TestProjectObservationPayload:
    @pytest.mark.parametrize("pull_numbers", [[], [0], [-1], [1, 1], list(range(1, 12))])
    def test_invalid_pull_selections_are_rejected(self, pull_numbers):
        with pytest.raises(ValidationError):
            ProjectObservationPayload(project_id=uuid4(), pull_numbers=pull_numbers)

    def test_payload_only_references_the_project_so_edits_are_never_stale(self):
        payload = ProjectObservationPayload(project_id=uuid4(), pull_numbers=[42])
        assert set(payload.model_dump()) == {"project_id", "pull_numbers"}


class TestTemplates:
    def test_every_profile_ships_a_readable_workflow_with_its_required_jobs(self):
        templates = list_templates()
        assert [template.id for template in templates] == [profile[0] for profile in TEMPLATE_PROFILES]
        for template in templates:
            assert template.filename == "ci.yml"
            assert template.version and template.changelog
            assert "pull_request" in template.content
            for job in template.required_jobs:
                assert f"{job}:" in template.content
