"""Read-only owed-item aggregate over owner models (`ADR-owed-items-aggregate-read`).

Each kind is one branch of a single UNION ALL. A page and a count are one statement each; no provider access.
Owner features keep their writes; a schema change there must update the predicate here and its tests.
"""

from collections.abc import Callable, Collection
from datetime import UTC, datetime
from uuid import UUID

from app.features.ai_catalogs.models import AICatalog
from app.features.project_management.connection_tests.models import ACTIVE, ConnectionTest
from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES, DecisionEntry, PipelineRun
from app.features.project_management.sdd.batch_models import SddActivityClaim, SddBatch, SddBatchMember
from app.features.project_management.work_plans.models import ItemDependency, WorkItem, WorkItemRecovery, WorkPlan
from app.features.project_management.work_plans.replacement_models import ReplacementAcceptance, ReplacementLink
from sqlalchemy import (
    DateTime,
    String,
    Uuid,
    and_,
    case,
    cast,
    exists,
    false,
    func,
    literal,
    null,
    or_,
    select,
    true,
    type_coerce,
    union_all,
)
from sqlalchemy.orm import aliased

COUNTED_RECOVERY_STATES = ("accepted", "reconciling")
COLUMNS = (
    "kind",
    "sort_key",
    "subject_id",
    "project_id",
    "waiting_since",
    "title",
    "state",
    "detail",
    "run_id",
    "work_plan_id",
    "work_item_id",
    "sdd_batch_id",
    "catalog_id",
    "catalog_hold",
    "catalog_available_at",
)


def _none(type_):
    return cast(null(), type_)


def _held_by_decision(run_id):
    """A run is held by a decision while it has any decision-inbox row (actionable or publication pending)."""
    held = aliased(DecisionEntry, name="held_decision")
    return exists().where(held.run_id == run_id)


def _counted_recovery(item_id):
    recovery = aliased(WorkItemRecovery, name="owed_recovery")
    return exists().where(recovery.item_id == item_id, recovery.state.in_(COUNTED_RECOVERY_STATES))


def _waiting_edge(original_item_id):
    """A waiting dependent of the original Item has no live acceptance on that edge."""
    edge = aliased(ItemDependency, name="owed_edge")
    dependent = aliased(WorkItem, name="owed_dependent")
    acceptance = aliased(ReplacementAcceptance, name="owed_acceptance")
    return exists().where(
        edge.depends_on_id == original_item_id,
        dependent.id == edge.item_id,
        dependent.state == "waiting",
        ~exists().where(
            acceptance.active == true(),
            acceptance.dependent_item_id == edge.item_id,
            acceptance.original_item_id == edge.depends_on_id,
        ),
    )


def _counted_replacement(item_id):
    link = aliased(ReplacementLink, name="owed_link")
    # SQLAlchemy correlates only with the immediately enclosing SELECT, so nested predicates name that level.
    return exists().where(link.original_item_id == item_id, link.active == true(), _waiting_edge(link.original_item_id))


def _batch_tables():
    return (
        aliased(SddActivityClaim, name="owed_claim"),
        aliased(SddBatchMember, name="owed_member"),
        aliased(SddBatch, name="owed_batch"),
    )


def _run_in_attention_batch(run_id):
    """The run is described by a listed batch: in attention and not itself yielding to a decision."""
    claim, member, batch = _batch_tables()
    return exists().where(
        claim.run_id == run_id,
        member.id == claim.member_id,
        batch.id == member.batch_id,
        batch.state == "attention",
        ~_batch_held_by_decision(batch.id),
    )


def _attention_batch_of(run_id):
    claim, member, batch = _batch_tables()
    return (
        select(batch.id)
        .where(claim.run_id == run_id, member.id == claim.member_id, batch.id == member.batch_id)
        .where(batch.state == "attention")
        .order_by(batch.id)
        .limit(1)
        .scalar_subquery()
    )


def _batch_held_by_decision(batch_id):
    claim = aliased(SddActivityClaim, name="decision_claim")
    member = aliased(SddBatchMember, name="decision_member")
    held = aliased(DecisionEntry, name="batch_decision")
    return exists().where(member.batch_id == batch_id, claim.member_id == member.id, held.run_id == claim.run_id)


def _branch(kind, subject, project_id, waiting_since, **values):
    """One union branch with the shared column order; absent context columns are typed NULLs."""
    defaults = {
        "title": _none(String),
        "state": _none(String),
        "detail": _none(String),
        "run_id": _none(Uuid),
        "work_plan_id": _none(Uuid),
        "work_item_id": _none(Uuid),
        "sdd_batch_id": _none(Uuid),
        "catalog_id": _none(Uuid),
        "catalog_hold": _none(String),
        "catalog_available_at": _none(DateTime(timezone=True)),
    }
    subject_text = cast(subject, String)
    columns = {
        "kind": literal(kind, String),
        "sort_key": literal(f"{kind}:", String) + subject_text,
        "subject_id": subject_text,
        "project_id": project_id,
        # type_coerce, not CAST: SQLite would turn a DATETIME cast of stored text into a number.
        "waiting_since": type_coerce(waiting_since, DateTime(timezone=True)),
        **defaults,
        **values,
    }
    return [columns[name].label(name) for name in COLUMNS], project_id


class OwedItemRepository:
    def _branches(self, now: datetime, cleanup_adapters: Collection[tuple[str, str]]) -> dict[str, Callable]:
        def decision():
            columns, project = _branch(
                "decision",
                DecisionEntry.key,
                DecisionEntry.project_id,
                DecisionEntry.waiting_since,
                title=DecisionEntry.title,
                state=DecisionEntry.kind,
                detail=DecisionEntry.question_state,
                run_id=DecisionEntry.run_id,
                sdd_batch_id=_attention_batch_of(DecisionEntry.run_id),
            )
            # The same predicate as the decision list's actionable count.
            statement = (
                select(*columns)
                .select_from(DecisionEntry)
                .join(PipelineRun, PipelineRun.id == DecisionEntry.run_id)
                .where(DecisionEntry.actionable == true(), PipelineRun.state.not_in(FINAL_RUN_STATES))
            )
            return statement, project

        def stopped_run():
            item = aliased(WorkItem, name="run_item")
            hold = case(
                (
                    or_(AICatalog.enabled == false(), AICatalog.availability_state.in_(("disabled", "unknown"))),
                    "unavailable",
                ),
                (
                    and_(
                        AICatalog.availability_state == "quota_blocked",
                        or_(AICatalog.available_at.is_(None), AICatalog.available_at > now),
                    ),
                    "quota-blocked",
                ),
                else_=None,
            )
            columns, project = _branch(
                "stopped-run",
                PipelineRun.id,
                PipelineRun.project_id,
                PipelineRun.updated_at,
                title=PipelineRun.pull_url,
                state=PipelineRun.state,
                detail=PipelineRun.pause_reason,
                run_id=PipelineRun.id,
                work_plan_id=item.plan_id,
                work_item_id=item.id,
                catalog_id=case((hold.is_not(None), AICatalog.id), else_=None),
                catalog_hold=hold,
                catalog_available_at=case((hold.is_not(None), AICatalog.available_at), else_=None),
            )
            statement = (
                select(*columns)
                .select_from(PipelineRun)
                .outerjoin(AICatalog, AICatalog.id == PipelineRun.ai_catalog_id)
                .outerjoin(item, item.pipeline_run_id == PipelineRun.id)
                .where(
                    PipelineRun.state.in_(("paused", "blocked")),
                    ~_held_by_decision(PipelineRun.id),
                    ~_run_in_attention_batch(PipelineRun.id),
                    or_(
                        item.id.is_(None),
                        and_(item.state != "attention", ~_counted_recovery(item.id), ~_counted_replacement(item.id)),
                    ),
                )
            )
            return statement, project

        def failed_run():
            item = aliased(WorkItem, name="failed_item")
            columns, project = _branch(
                "failed-run",
                PipelineRun.id,
                PipelineRun.project_id,
                PipelineRun.updated_at,
                title=PipelineRun.pull_url,
                state=PipelineRun.state,
                detail=PipelineRun.pause_reason,
                run_id=PipelineRun.id,
                work_plan_id=item.plan_id,
                work_item_id=item.id,
            )
            statement = (
                select(*columns)
                .select_from(PipelineRun)
                .outerjoin(item, item.pipeline_run_id == PipelineRun.id)
                .where(
                    PipelineRun.state == "failed",
                    ~_run_in_attention_batch(PipelineRun.id),
                    or_(
                        item.id.is_(None),
                        and_(item.state != "attention", ~_counted_recovery(item.id), ~_counted_replacement(item.id)),
                    ),
                )
            )
            return statement, project

        def work_plan_proposed():
            columns, project = _branch(
                "work-plan-proposed",
                WorkPlan.id,
                WorkPlan.project_id,
                WorkPlan.updated_at,
                title=WorkPlan.title,
                state=WorkPlan.state,
                work_plan_id=WorkPlan.id,
            )
            return select(*columns).select_from(WorkPlan).where(WorkPlan.state == "proposed"), project

        def work_item_recovery():
            columns, project = _branch(
                "work-item-recovery",
                WorkItemRecovery.id,
                WorkItemRecovery.project_id,
                WorkItemRecovery.created_at,
                title=WorkItem.title,
                state=WorkItemRecovery.state,
                detail=WorkItemRecovery.detail,
                run_id=WorkItem.pipeline_run_id,
                work_plan_id=WorkItemRecovery.plan_id,
                work_item_id=WorkItemRecovery.item_id,
            )
            statement = (
                select(*columns)
                .select_from(WorkItemRecovery)
                .join(WorkItem, WorkItem.id == WorkItemRecovery.item_id)
                .where(
                    WorkItemRecovery.state.in_(COUNTED_RECOVERY_STATES),
                    or_(WorkItem.pipeline_run_id.is_(None), ~_held_by_decision(WorkItem.pipeline_run_id)),
                )
            )
            return statement, project

        def work_item_replacement():
            original = aliased(WorkItem, name="replaced_item")
            columns, project = _branch(
                "work-item-replacement",
                ReplacementLink.id,
                ReplacementLink.project_id,
                ReplacementLink.updated_at,
                title=original.title,
                state=literal("active", String),
                detail=ReplacementLink.reason,
                work_plan_id=ReplacementLink.original_plan_id,
                work_item_id=ReplacementLink.original_item_id,
            )
            statement = (
                select(*columns)
                .select_from(ReplacementLink)
                .join(original, original.id == ReplacementLink.original_item_id)
                .where(ReplacementLink.active == true(), _waiting_edge(ReplacementLink.original_item_id))
            )
            return statement, project

        def work_item_attention():
            columns, project = _branch(
                "work-item-attention",
                WorkItem.id,
                WorkPlan.project_id,
                WorkItem.updated_at,
                title=WorkItem.title,
                state=WorkItem.state,
                detail=WorkItem.detail,
                run_id=WorkItem.pipeline_run_id,
                work_plan_id=WorkItem.plan_id,
                work_item_id=WorkItem.id,
            )
            statement = (
                select(*columns)
                .select_from(WorkItem)
                .join(WorkPlan, WorkPlan.id == WorkItem.plan_id)
                .where(
                    WorkItem.state == "attention",
                    or_(WorkItem.pipeline_run_id.is_(None), ~_held_by_decision(WorkItem.pipeline_run_id)),
                    ~_counted_recovery(WorkItem.id),
                    ~_counted_replacement(WorkItem.id),
                )
            )
            return statement, project

        def sdd_batch_attention():
            columns, project = _branch(
                "sdd-batch-attention",
                SddBatch.id,
                SddBatch.project_id,
                SddBatch.updated_at,
                state=SddBatch.state,
                detail=SddBatch.detail,
                sdd_batch_id=SddBatch.id,
            )
            statement = (
                select(*columns)
                .select_from(SddBatch)
                .where(SddBatch.state == "attention", ~_batch_held_by_decision(SddBatch.id))
            )
            return statement, project

        def connection_test_cleanup():
            columns, project = _branch(
                "connection-test-cleanup",
                ConnectionTest.id,
                ConnectionTest.project_id,
                func.coalesce(ConnectionTest.finished_at, ConnectionTest.updated_at),
                title=ConnectionTest.repository,
                state=ConnectionTest.cleanup_status,
                detail=ConnectionTest.detail,
            )
            snapshot = ConnectionTest.catalog_snapshot
            adapter = (
                or_(
                    *(
                        and_(snapshot["kind"].as_string() == kind, snapshot["adapter"].as_string() == key)
                        for kind, key in cleanup_adapters
                    )
                )
                if cleanup_adapters
                else false()
            )
            unconfirmed = ConnectionTest.evidence["unconfirmed_pulls"].as_string()
            statement = (
                select(*columns)
                .select_from(ConnectionTest)
                .where(
                    ConnectionTest.status != ACTIVE,
                    ConnectionTest.cleanup_status != "completed",
                    adapter,
                    or_(
                        ConnectionTest.evidence["output_discovery_pending"].as_boolean() == true(),
                        and_(unconfirmed.is_not(None), unconfirmed.not_in(("{}", "null", ""))),
                    ),
                )
            )
            return statement, project

        return {
            "decision": decision,
            "stopped-run": stopped_run,
            "work-plan-proposed": work_plan_proposed,
            "work-item-recovery": work_item_recovery,
            "work-item-replacement": work_item_replacement,
            "work-item-attention": work_item_attention,
            "sdd-batch-attention": sdd_batch_attention,
            "connection-test-cleanup": connection_test_cleanup,
            "failed-run": failed_run,
        }

    def _union(self, now, cleanup_adapters, project_id: UUID | None, kind: str | None):
        statements = []
        for name, build in self._branches(now, cleanup_adapters).items():
            if kind is not None and name != kind:
                continue
            statement, project = build()
            if project_id is not None:
                statement = statement.where(project == project_id)
            statements.append(statement)
        return union_all(*statements).subquery("owed") if len(statements) > 1 else statements[0].subquery("owed")

    async def page(self, session, *, now, cleanup_adapters, project_id, kind, after, limit):
        owed = self._union(now, cleanup_adapters, project_id, kind)
        waiting = owed.c.waiting_since
        sqlite = session.get_bind().dialect.name == "sqlite"
        if sqlite:
            # SQLite keeps timestamps as text in mixed precision ("...:54" from server defaults, "...:54.000000" from
            # binds); compare and order on julianday so equal instants compare equal.
            waiting = func.julianday(waiting)
        statement = select(owed)
        if after:
            timestamp, key = after
            bound = func.julianday(timestamp.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")) if sqlite else timestamp
            statement = statement.where(or_(waiting > bound, and_(waiting == bound, owed.c.sort_key > key)))
        statement = statement.order_by(waiting, owed.c.sort_key).limit(limit + 1)
        return list((await session.execute(statement)).mappings().all())

    async def counts(self, session, *, now, cleanup_adapters, project_id):
        owed = self._union(now, cleanup_adapters, project_id, None)
        statement = select(owed.c.kind, owed.c.project_id, func.count()).group_by(owed.c.kind, owed.c.project_id)
        return [(kind, project, count) for kind, project, count in (await session.execute(statement)).all()]
