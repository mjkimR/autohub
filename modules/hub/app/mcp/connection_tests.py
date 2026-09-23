from app.mcp.contracts import Items, StartTest, TestFilter, TestId, TestView, TestWait
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app.mcp.waiting import wait_for_change
from app_mcp import ToolRegistry


def register_connection_tests(registry: ToolRegistry, deps: Dependencies) -> None:
    async def start(args: StartTest) -> TestView:
        return TestView.from_read(await deps.tests.start(args.project_id, args.request_id, args.ai_catalog_id))

    async def list_tests(args: TestFilter) -> Items[TestView]:
        tests = await deps.tests.list(args.project_id)
        return Items(items=[TestView.from_read(test) for test in tests[: args.limit]], total_count=len(tests))

    async def get(args: TestWait) -> TestView:
        async def read() -> TestView:
            return TestView.from_read(await deps.tests.get(args.project_id, args.test_id))

        return await wait_for_change(
            read,
            lambda test: (
                test.status,
                test.phase,
                test.cleanup_status,
                test.detail,
                tuple(sorted(test.evidence.items())),
            ),
            lambda test: test.settled,
            args.wait_seconds,
        )

    async def cancel(args: TestId) -> TestView:
        return TestView.from_read(await deps.tests.cancel(args.project_id, args.test_id))

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
        "connection_tests.list",
        "List a project's recent connection tests with outcome, evidence links and cleanup status, newest first.",
        TestFilter,
        Items[TestView],
        list_tests,
    )
    register(
        registry,
        "connection_tests.get",
        "Read connection-test progress, evidence links and cleanup status. Set wait_seconds to wait for the next change; the test is done when status is not running and cleanup is completed or failed.",
        TestWait,
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
