from app.mcp.contracts import StartTest, TestId, TestView
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app_mcp import ToolRegistry


def register_connection_tests(registry: ToolRegistry, deps: Dependencies) -> None:
    async def start(args: StartTest) -> TestView:
        return TestView.model_validate(await deps.tests.start(args.project_id, args.request_id, args.ai_catalog_id))

    async def get(args: TestId) -> TestView:
        return TestView.model_validate(await deps.tests.get(args.project_id, args.test_id))

    async def cancel(args: TestId) -> TestView:
        return TestView.model_validate(await deps.tests.cancel(args.project_id, args.test_id))

    register(
        registry,
        "connection_tests.start",
        "Queue an isolated provider/CI test that can create a temporary branch and PR. Reuse request_id on retries; the scheduler progresses work and cleanup.",
        StartTest,
        TestView,
        start,
        write=True,
    )
    register(
        registry,
        "connection_tests.get",
        "Read connection-test progress and cleanup status. Cleanup must complete even after cancellation.",
        TestId,
        TestView,
        get,
    )
    register(
        registry,
        "connection_tests.cancel",
        "Request test cancellation and advance cleanup once. If the response is lost, get the test again; cleanup continues in the scheduler.",
        TestId,
        TestView,
        cancel,
        write=True,
    )
