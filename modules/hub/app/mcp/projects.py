from app.mcp.contracts import (
    CatalogView,
    ConnectorView,
    CreateProject,
    Items,
    Page,
    ProjectId,
    ProjectLookup,
    ProjectView,
    ReadinessView,
    Search,
    UpdateProject,
)
from app.mcp.dependencies import Dependencies, connector_reader
from app.mcp.names import catalog_keys, connector_names
from app.mcp.registration import register
from app_layer_base.base.repos.query_options import ListQueryOptions
from app_mcp import ToolRegistry


def register_projects(registry: ToolRegistry, deps: Dependencies) -> None:
    async def views(rows) -> list[ProjectView]:
        connectors, catalogs = await connector_names(), await catalog_keys(deps)
        result = []
        for row in rows:
            project = ProjectView.model_validate(row)
            if project.github is not None:
                project.github_connector_name = connectors.get(project.github.github_connector_id)
                if project.github.ai_catalog_id is not None:
                    project.ai_catalog_key = catalogs.get(project.github.ai_catalog_id)
            result.append(project)
        return result

    async def view(row) -> ProjectView:
        return (await views([row]))[0]

    async def list_projects(args: Search) -> Items[ProjectView]:
        result = await deps.projects.list(args.offset, args.limit, args.search)
        return Items(items=await views(result.items), total_count=result.total_count)

    async def get_project(args: ProjectLookup) -> ProjectView:
        if args.repository is not None:
            return await view(await deps.projects.get_by_repository(args.repository))
        assert args.project_id is not None
        return await view(await deps.projects.get(args.project_id))

    async def create_project(args: CreateProject) -> ProjectView:
        return await view(await deps.projects.create(args.project))

    async def update_project(args: UpdateProject) -> ProjectView:
        return await view(await deps.projects.patch(args.project_id, args.project))

    async def list_catalogs(args: Page) -> Items[CatalogView]:
        result = await deps.catalogs.list()
        return Items(
            items=[CatalogView.model_validate(row) for row in result.items[args.offset : args.offset + args.limit]],
            total_count=len(result.items),
        )

    async def list_connectors(args: Page) -> Items[ConnectorView]:
        result = await connector_reader().execute(ListQueryOptions(offset=args.offset, limit=args.limit))
        return Items(
            items=[ConnectorView.model_validate(row) for row in result.items], total_count=result.total_count or 0
        )

    async def readiness(args: ProjectId) -> Items[ReadinessView]:
        options = await deps.tests.options(args.project_id)
        return Items(items=[ReadinessView.from_option(option) for option in options], total_count=len(options))

    register(
        registry,
        "projects.list",
        "Find projects by name or owner/repository; use the returned project ID.",
        Search,
        Items[ProjectView],
        list_projects,
    )
    register(
        registry,
        "projects.get",
        "Read project configuration and revision by project_id or owner/repository; use the returned ID for other tools.",
        ProjectLookup,
        ProjectView,
        get_project,
    )
    register(
        registry,
        "projects.create",
        "Connect a repository using an existing connector. Automation defaults apply. On conflict, find the existing project; do not blindly retry.",
        CreateProject,
        ProjectView,
        create_project,
        write=True,
    )
    register(
        registry,
        "projects.update",
        "Change only the fields you send, using expected_revision from projects.get; stale revisions fail. Nested objects merge, lists replace, github=null disconnects.",
        UpdateProject,
        ProjectView,
        update_project,
        write=True,
    )
    register(
        registry,
        "catalogs.list",
        "List catalog IDs, provider capabilities and current capacity; credentials and policy internals are omitted.",
        Page,
        Items[CatalogView],
        list_catalogs,
    )
    register(
        registry,
        "connectors.list",
        "List existing connector names, IDs and readiness. Create or rotate credentials in the AutoHub UI.",
        Page,
        Items[ConnectorView],
        list_connectors,
    )
    register(
        registry,
        "projects.readiness",
        "Per catalog, whether a connection test can start and which requirements are missing or need manual confirmation. This does not contact providers or prove CI readiness; start a connection test to verify it.",
        ProjectId,
        Items[ReadinessView],
        readiness,
    )
