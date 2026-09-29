from app.features.project_management.projects.errors import ProjectError
from app.mcp.contracts import (
    CatalogView,
    ConnectorView,
    CreateProject,
    Items,
    ProjectChange,
    ProjectLookup,
    ProjectOptions,
    ProjectOptionsRequest,
    ProjectUpdateView,
    ProjectView,
    ReadinessReport,
    ReadinessRequest,
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

    async def update_project(args: UpdateProject) -> ProjectUpdateView:
        before, proposed = await deps.projects.preview_patch(args.project_id, args.project)
        fields = {"name", "enabled", "github"}
        changes = project_changes(
            before.model_dump(mode="json", include=fields), proposed.model_dump(mode="json", include=fields)
        )
        result = proposed if args.dry_run else await deps.projects.patch(args.project_id, args.project)
        return ProjectUpdateView(**(await view(result)).model_dump(), applied=not args.dry_run, changes=changes)

    async def options(args: ProjectOptionsRequest) -> ProjectOptions:
        project = await deps.projects.get(args.project_id) if args.project_id is not None else None
        all_catalogs = (await deps.catalogs.list()).items
        catalogs = [
            item
            for item in all_catalogs
            if (not args.enabled_only or item.enabled) and (args.capability is None or getattr(item, args.capability))
        ]
        result = ProjectOptions(
            catalogs=Items(
                items=[CatalogView.model_validate(row) for row in catalogs[args.offset : args.offset + args.limit]],
                total_count=len(catalogs),
            )
        )
        if project is not None:
            selected_id = project.github.ai_catalog_id if project.github else None
            selected = (
                next((item for item in all_catalogs if item.id == selected_id), None)
                if selected_id
                else next((item for item in all_catalogs if item.key == "personal-codex"), None)
            )
            result.selection_source = "project" if selected_id else "default"
            result.selected_catalog_id = selected.id if selected else selected_id
            result.selected_catalog_key = selected.key if selected else (None if selected_id else "personal-codex")
        if args.connectors_page is not None:
            page = args.connectors_page
            rows = await connector_reader().execute(ListQueryOptions(offset=page.offset, limit=page.limit))
            result.connectors = Items(
                items=[ConnectorView.model_validate(row) for row in rows.items], total_count=rows.total_count or 0
            )
        return result

    async def readiness(args: ReadinessRequest) -> ReadinessReport:
        options = await deps.tests.options(args.project_id)
        if args.ai_catalog_id is not None:
            options = [option for option in options if option.ai_catalog_id == args.ai_catalog_id]
            if not options:
                raise ProjectError(
                    404,
                    "No connection-test option for this catalog",
                    fix="Use projects_options with capability=connection_test to find a supported catalog.",
                )
        return ReadinessReport(
            items=[ReadinessView.from_option(option) for option in options], total_count=len(options)
        )

    register(
        registry,
        "projects_list",
        "Find projects by name or owner/repository; use the returned project ID.",
        Search,
        Items[ProjectView],
        list_projects,
    )
    register(
        registry,
        "projects_get",
        "Read project configuration and revision by project_id or owner/repository; use the returned ID for other tools.",
        ProjectLookup,
        ProjectView,
        get_project,
    )
    register(
        registry,
        "projects_create",
        "Operator onboarding: find any existing project first, then connect the repository using an existing connector and verified CI contract. Explicitly set github.automation.auto_merge; all effective automation settings are returned. On conflict, find the existing project; do not blindly retry.",
        CreateProject,
        ProjectView,
        create_project,
        write=True,
        ops=True,
    )
    register(
        registry,
        "projects_update",
        "Patch configuration using expected_revision from projects_get. Set dry_run=true to validate and inspect changed paths without saving; apply the same patch/revision to save. Nested objects merge, lists replace, github=null disconnects. A preview is optional and does not reserve the revision.",
        UpdateProject,
        ProjectUpdateView,
        update_project,
        write=True,
        ops=True,
    )
    register(
        registry,
        "projects_options",
        "Read catalog choices and capacity; filter by capability/enabled_only and pass project_id to identify its configured selection. For onboarding or connection changes, include connectors_page={} for credential-free connector choices. Catalog and connector pages are independent. Skip when the current project selection suffices.",
        ProjectOptionsRequest,
        ProjectOptions,
        options,
    )
    register(
        registry,
        "projects_readiness",
        "For onboarding, configuration changes or readiness diagnosis, report per catalog whether a connection test can start and which requirements are missing or need manual confirmation. This does not contact providers or prove CI readiness; an operator can start a connection test to verify it. Filter ai_catalog_id to inspect one catalog. status distinguishes blocked, manual_checks and configured. Not required before every run.",
        ReadinessRequest,
        ReadinessReport,
        readiness,
    )


def project_changes(before: dict, after: dict, prefix: str = "") -> list[ProjectChange]:
    changes = []
    for key in sorted(before.keys() | after.keys()):
        previous, current = before.get(key), after.get(key)
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(previous, dict) and isinstance(current, dict):
            changes.extend(project_changes(previous, current, path))
        elif previous != current:
            changes.append(ProjectChange(path=path, before=previous, after=current))
    return changes
