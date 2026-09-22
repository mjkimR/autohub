"""Serializable recipe metadata. The UI renders this contract without provider switches."""

from typing import Literal

from pydantic import BaseModel, Field


class TestRequirement(BaseModel):
    key: str
    label: str
    description: str
    source: Literal["project_github", "catalog_connector", "manual"]
    provider: str | None = None
    url: str | None = None


class TestEvidence(BaseModel):
    key: str
    label: str
    # Links are limited to explicit trusted origins; text evidence has no origin.
    origin: str | None = None


class ConnectionTestSpec(BaseModel):
    key: str
    version: int = 1
    title: str
    description: str
    connector_provider: str | None = None
    create_once: bool = False
    discovers_output_pr: bool = False
    manual_cleanup_resolution: bool = False
    delivery_key: str
    requirements: list[TestRequirement]
    phases: dict[str, str] = Field(default_factory=dict)
    evidence: list[TestEvidence] = Field(default_factory=list)


GITHUB_REQUIREMENT = TestRequirement(
    key="github",
    label="GitHub repository access",
    source="project_github",
    provider="github",
    description="Configure the project repository and an enabled GitHub connector with Contents and Pull requests read/write access.",
)
COMMON_PHASES = {
    "preparing": "Checking access and preparing test branch",
    "dispatching": "Waiting for catalog admission / sending request",
    "verifying_ci": "Verifying CI",
    "verified": "Verified",
}
COMMON_EVIDENCE = [
    TestEvidence(key="pull_url", label="Test PR", origin="https://github.com"),
    TestEvidence(key="ci_status", label="CI"),
    TestEvidence(key="ci_url", label="CI run", origin="https://github.com"),
]
CODEX_SPEC = ConnectionTestSpec(
    key="codex-github-mention",
    title="Codex PR mention test",
    delivery_key="comment_id",
    description="Posts @codex from the project's GitHub account on an isolated Draft PR, then verifies its pushed change and CI. Selecting a catalog does not switch the GitHub/Codex account.",
    requirements=[
        GITHUB_REQUIREMENT,
        TestRequirement(
            key="codex_account",
            label="Codex GitHub connection",
            source="manual",
            description="Connect the same GitHub account in Codex and grant access to this repository.",
            url="https://chatgpt.com/codex",
        ),
        TestRequirement(
            key="codex_environment",
            label="Codex cloud environment",
            source="manual",
            description="Create the repository environment, configure its setup script, and allow agent access to github.com. Provide GH_TOKEN with push access during the agent phase; setup-only secrets are removed before that phase.",
            url="https://chatgpt.com/codex/settings/environments",
        ),
        TestRequirement(
            key="ci",
            label="Draft PR CI",
            source="manual",
            description="AGENTS.md must list repository checks. Required CI must run on Draft PRs and the test fixture path.",
        ),
    ],
    phases={**COMMON_PHASES, "waiting_for_push": "Waiting for test change"},
    evidence=[
        *COMMON_EVIDENCE,
        TestEvidence(key="comment_url", label="Request", origin="https://github.com"),
        TestEvidence(key="reply_url", label="Codex response", origin="https://github.com"),
    ],
)
JULES_SPEC = ConnectionTestSpec(
    key="jules-api",
    title="Jules session PR test",
    connector_provider="jules",
    create_once=True,
    discovers_output_pr=True,
    manual_cleanup_resolution=True,
    delivery_key="session_name",
    description="Uses the catalog's Jules API connector to start a session on an isolated branch, then verifies its generated PR and CI. Test sessions never enter normal task PR adoption.",
    requirements=[
        GITHUB_REQUIREMENT,
        TestRequirement(
            key="jules_connector",
            label="Jules API connector",
            source="catalog_connector",
            provider="jules",
            description="Assign an enabled Jules API key connector to this AI catalog.",
            url="/settings/ai-catalogs",
        ),
        TestRequirement(
            key="jules_source",
            label="Jules repository connection",
            source="manual",
            description="Connect this repository in Jules. The preflight checks its actual Source resource.",
            url="https://jules.google.com/",
        ),
        TestRequirement(
            key="ci",
            label="Isolated branch CI",
            source="manual",
            description="Required CI must run on Draft PRs targeting autohub-connection-test/** and include the test fixture path.",
        ),
    ],
    phases={**COMMON_PHASES, "waiting_for_session": "Waiting for Jules session and PR"},
    evidence=[
        *COMMON_EVIDENCE,
        TestEvidence(key="session_state", label="Session"),
        TestEvidence(key="session_url", label="Jules session", origin="https://jules.google.com"),
    ],
)
