import pytest
from app.mcp.registration import register
from app_mcp import ToolRegistry
from pydantic import BaseModel

pytestmark = pytest.mark.unit


async def handler(args: BaseModel) -> BaseModel:
    return args


@pytest.mark.parametrize(
    "name", ["projects.list", "runs-enroll", "Projects_list", "도구", "runs__get", "runs_", "", "a" * 65]
)
def test_rejects_nonportable_names_before_registration(name):
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="snake_case"):
        register(registry, name, "Description", BaseModel, BaseModel, handler)
    assert registry.definitions() == ()


def test_accepts_snake_case_at_length_boundary():
    registry = ToolRegistry()
    name = "a_" + "b" * 62
    register(registry, name, "Description", BaseModel, BaseModel, handler)
    assert registry.definitions()[0].name == name
