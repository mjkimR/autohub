import pytest
from app.features import tasks
from httpx import AsyncClient

from tests.utils.assertions import assert_status_code


@pytest.mark.integration
class TestTasksAPI:
    _base_url = "/api/v1/tasks"

    async def test_get_task_specs_success(self, client: AsyncClient):
        # Manually trigger autodiscover since test client doesn't trigger lifespan
        tasks.autodiscover()

        response = await client.get(f"{self._base_url}/specs")

        assert_status_code(response, 200)
        data = response.json()
        assert isinstance(data, list)

        # 'hello_world' should be there if autodiscover worked
        hello_world = next((t for t in data if t["name"] == "hello_world"), None)
        assert hello_world is not None
        assert hello_world["description"] == "Example task. Registered as 'hello_world'."
        assert hello_world["payload_schema"] is not None
        assert hello_world["payload_schema"]["title"] == "HelloWorldPayload"

    async def test_no_payload_task_is_in_specs(self, client: AsyncClient):
        """no_payload_task should appear in specs with payload_schema=None."""
        tasks.autodiscover()

        response = await client.get(f"{self._base_url}/specs")

        assert_status_code(response, 200)
        data = response.json()

        no_payload = next((t for t in data if t["name"] == "no_payload_task"), None)
        assert no_payload is not None
        assert no_payload["description"] == "Example task with no payload. Registered as 'no_payload_task'."
        assert no_payload["payload_schema"] is None
