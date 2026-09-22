import subprocess
import sys

import httpx
import pytest
from app.features.ai_catalogs.providers.jules import JulesApiError, JulesClient


async def test_source_resolution_follows_pages_and_uses_opaque_name():
    requests = []

    def respond(request):
        requests.append(request)
        if "pageToken" not in request.url.params:
            return httpx.Response(200, json={"sources": [], "nextPageToken": "next"})
        assert request.url.params["pageToken"] == "next"
        return httpx.Response(
            200,
            json={
                "sources": [
                    {
                        "name": "sources/opaque-resource",
                        "githubRepo": {"owner": "Owner", "repo": "App"},
                    }
                ]
            },
        )

    async with httpx.AsyncClient(
        base_url="https://jules.googleapis.com/v1alpha/", transport=httpx.MockTransport(respond)
    ) as http:
        assert await JulesClient(http).resolve_source("owner/app") == "sources/opaque-resource"
    assert len(requests) == 2


async def test_missing_source_never_fabricates_a_resource_name():
    async with httpx.AsyncClient(
        base_url="https://jules.googleapis.com/v1alpha/",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"sources": []})),
    ) as http:
        with pytest.raises(JulesApiError, match="Connect this repository") as error:
            await JulesClient(http).resolve_source("owner/app")
        assert error.value.status_code == 422


def test_connection_service_import_does_not_import_task_registration_packages():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from app.features.project_management.connection_tests.services import ConnectionTestService; assert not any(k.startswith('app.features.execution.tasks.domains') for k in sys.modules)",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
