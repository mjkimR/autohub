"""Safe replacement evidence: never include task text or arbitrary event maps."""

from uuid import UUID

from app.features.project_management.work_plans.replacement_schemas import ReplacementResult
from app.mcp.delivery_views import View
from pydantic import Field


class EndpointView(View):
    plan_id: UUID
    item_id: UUID
    key: str
    title: str
    digest: str
    plan_revision: int
    plan_state: str
    item_state: str
    repository: str
    connector_id: UUID
    target: str
    branch: str | None
    execution_id: UUID | None
    pull_number: int | None
    pull_url: str | None
    merge_sha: str | None
    completed_at: str | None


class SnapshotView(View):
    original: EndpointView
    replacement: EndpointView


class AcceptanceView(View):
    id: UUID
    dependent_item_id: UUID
    active: bool
    consumed: bool
    snapshot: SnapshotView
    actor: str
    reason: str


class EventView(View):
    id: UUID
    acceptance_id: UUID | None
    kind: str
    actor: str
    reason: str
    revision: int
    created_at: str


class LinkView(View):
    id: UUID
    active: bool
    snapshot: SnapshotView
    current_replacement: EndpointView
    actor: str
    reason: str
    acceptances: list[AcceptanceView] = Field(max_length=100)
    acceptance_count: int
    acceptances_omitted: bool
    events: list[EventView] = Field(max_length=100)
    event_offset: int
    event_total_count: int
    events_omitted: bool


class ReplacementView(View):
    original: EndpointView
    candidate: EndpointView | None
    evidence_revision: int
    links: list[LinkView] = Field(max_length=100)
    link_count: int
    links_omitted: bool
    history_offset: int
    history_total_count: int
    history_limit: int
    result: ReplacementResult | None


def replacement_view(row) -> ReplacementView:
    data = row.model_dump()
    links = []
    # Preserve active or consumed evidence before optional history when capping.
    ordered = sorted(
        data["links"], key=lambda link: not (link["active"] or any(a["consumed"] for a in link["acceptances"]))
    )
    for link in ordered[:100]:
        acceptances = sorted(link["acceptances"], key=lambda a: not (a["active"] or a["consumed"]))
        links.append(
            LinkView.model_validate(
                link
                | {
                    "acceptances": acceptances[:100],
                    "acceptance_count": len(acceptances),
                    "acceptances_omitted": len(acceptances) > 100,
                    "events": link["events"][:100],
                    "events_omitted": link["event_offset"] + min(100, len(link["events"])) < link["event_total_count"],
                }
            )
        )
    return ReplacementView.model_validate(
        data
        | {
            "links": links,
            "link_count": len(data["links"]),
            "links_omitted": len(data["links"]) > 100,
        }
    )
