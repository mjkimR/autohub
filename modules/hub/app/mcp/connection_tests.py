from app.mcp.contracts import StartTest, TestFilter, TestId, TestList, TestView, TestWait
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app.mcp.waiting import wait_for_change
from app_mcp import ToolRegistry


def register_connection_tests(registry: ToolRegistry, deps: Dependencies) -> None:
    async def start(args: StartTest) -> TestView:
        return TestView.from_read(
            await deps.tests.start(
                args.project_id,
                args.request_id,
                args.ai_catalog_id,
                expected_project_revision=args.expected_project_revision,
            )
        )

    async def list_tests(args: TestFilter) -> TestList:
        tests = await deps.tests.list(args.project_id)
        tests = [
            test
            for test in tests
            if (args.ai_catalog_id is None or test.ai_catalog_id == args.ai_catalog_id)
            and (args.status is None or test.status == args.status)
            and (args.configuration_current is None or test.configuration_current == args.configuration_current)
        ]
        end = args.offset + args.limit
        return TestList(
            items=[TestView.from_read(test) for test in tests[args.offset : end]],
            total_count=len(tests),
            next_offset=end if end < len(tests) else None,
        )

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
        "connection_tests_start",
        "Operator onboarding/configuration validation, not a prerequisite for each run: queue an isolated provider/CI test that can create a temporary branch and PR. Reuse request_id on retries; it is also the test_id, so recover via connection_tests_get even after a lost response. Optionally pass expected_project_revision from projects_get to guard new tests. Existing request IDs replay before that check. The scheduler progresses work and cleanup; follow next_action until settled.",
        StartTest,
        TestView,
        start,
        write=True,
        ops=True,
    )
    register(
        registry,
        "connection_tests_list",
        "Recover a lost test ID or inspect prior validation; use get directly when the ID is known. Filter by catalog, status or configuration_current and paginate with next_offset. Results and total_count cover only the latest history_limit=30 entries, newest first; use get for older known IDs.",
        TestFilter,
        TestList,
        list_tests,
    )
    register(
        registry,
        "connection_tests_get",
        "Read connection-test progress, evidence links and cleanup status. Set wait_seconds to wait for the next change; the test is done when status is not running and cleanup is completed or failed.",
        TestWait,
        TestView,
        get,
    )
    register(
        registry,
        "connection_tests_cancel",
        "Request test cancellation and advance cleanup once. If the response is lost, get the test again; cleanup continues in the scheduler.",
        TestId,
        TestView,
        cancel,
        write=True,
        ops=True,
    )
