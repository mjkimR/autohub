from autohub_sdk import RunRequest
from pydantic import Field


class PinnedRunRequest(RunRequest):
    """Optional host extension; existing SDK 0.2 requests remain valid."""

    expected_release_id: str | None = Field(default=None, min_length=1, max_length=128)
    expected_release_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
