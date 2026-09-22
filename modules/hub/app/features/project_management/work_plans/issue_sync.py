"""Best-effort outbound records. Failures never gate work admission or completion."""

import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

from app.features.project_management.pipelines import services as github_services
from app.features.project_management.pipelines.github import GitHubObservationError
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.work_plans.github import WorkGitHub
from app.features.project_management.work_plans.mirror_records import refresh_mirrors
from app.features.project_management.work_plans.models import WorkIssueMirror, WorkPlan
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import or_, select, update


class WorkIssueSync:
    def __init__(self, observer: PipelineObservationService):
        self.observer = observer

    async def execute(self, *, limit: int = 4) -> None:
        # Serial, bounded publication; each attempt gets a durable cooldown and lease.
        for _ in range(limit):
            now, lease = get_current_utc_time(), uuid4()
            async with AsyncTransaction() as session:
                row = await session.scalar(
                    select(WorkIssueMirror)
                    .where(
                        or_(
                            WorkIssueMirror.synced_digest.is_(None),
                            WorkIssueMirror.synced_digest != WorkIssueMirror.digest,
                        ),
                        or_(WorkIssueMirror.next_action_at.is_(None), WorkIssueMirror.next_action_at <= now),
                        or_(WorkIssueMirror.lease_expires_at.is_(None), WorkIssueMirror.lease_expires_at <= now),
                    )
                    .order_by(
                        WorkIssueMirror.next_action_at.nullsfirst(), WorkIssueMirror.created_at, WorkIssueMirror.id
                    )
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                if row is None:
                    return
                updated = await session.execute(
                    update(WorkIssueMirror)
                    .where(
                        WorkIssueMirror.id == row.id,
                        or_(WorkIssueMirror.lease_expires_at.is_(None), WorkIssueMirror.lease_expires_at <= now),
                    )
                    .values(
                        lease_token=lease,
                        lease_expires_at=now + timedelta(seconds=90),
                        next_action_at=now + timedelta(minutes=5),
                    )
                    .returning(WorkIssueMirror.id)
                    .execution_options(synchronize_session="fetch")
                )
                if updated.scalar_one_or_none() is None:
                    continue
                plan = await session.get(WorkPlan, row.plan_id)
                assert plan is not None
                row.lease_token = lease
            try:
                async with asyncio.timeout(40):
                    token = await self.observer.get_token(plan.connector_id, "github")
                    async with github_services.create_github_client(token) as client:
                        await self.publish(plan, row, WorkGitHub(client))
            except Exception as exc:
                detail = (
                    str(exc) if isinstance(exc, GitHubObservationError) else "Issue synchronization failed; will retry"
                )
                async with AsyncTransaction() as session:
                    current = await self.leased(session, row.id, lease)
                    if current:
                        current.error = detail
                        if isinstance(exc, GitHubObservationError):
                            if exc.retry_after:
                                current.next_action_at = get_current_utc_time() + timedelta(seconds=exc.retry_after)
                            if exc.status_code in (401, 403, 422, 429) and current.issue_number is None:
                                current.create_attempted = False
            finally:
                async with AsyncTransaction() as session:
                    current = await self.leased(session, row.id, lease)
                    if current:
                        current.lease_token, current.lease_expires_at = None, None
            await asyncio.sleep(1)

    async def leased(self, session, id, token):
        return await session.scalar(
            select(WorkIssueMirror)
            .where(
                WorkIssueMirror.id == id,
                WorkIssueMirror.lease_token == token,
                WorkIssueMirror.lease_expires_at > get_current_utc_time(),
            )
            .with_for_update()
        )

    async def find_issue(self, plan: WorkPlan, row: WorkIssueMirror, github: WorkGitHub):
        login = await github.reader.current_login()
        marker = f"<!-- autohub-work:{row.entity_id} -->"
        for page in range(1, 11):
            issues = await github.reader._get_list(
                f"/repos/{plan.repository}/issues",
                {
                    "state": "all",
                    "creator": login,
                    "sort": "created",
                    "direction": "desc",
                    "per_page": 100,
                    "page": page,
                },
            )
            for issue in issues:
                if "pull_request" not in issue and marker in (issue.get("body") or ""):
                    return issue
            if len(issues) < 100:
                return None
        raise GitHubObservationError("Issue identity scan exceeded its budget; synchronization is pending")

    async def publish(self, plan: WorkPlan, row: WorkIssueMirror, github: WorkGitHub):
        desired, root = row.desired, f"/repos/{plan.repository}"
        if row.issue_number is None:
            issue = await self.find_issue(plan, row, github) if row.create_attempted else None
            if issue is None:
                if row.create_attempted:
                    raise GitHubObservationError(
                        "Issue creation was uncertain and no matching record was found; no duplicate was created"
                    )
                async with AsyncTransaction() as session:
                    current = await self.leased(session, row.id, row.lease_token)
                    if current is None:
                        return
                    current.create_attempted = True
                issue = await github.write(
                    "POST",
                    f"{root}/issues",
                    {
                        "title": desired["title"],
                        "body": desired["body"],
                    },
                )
            async with AsyncTransaction() as session:
                current = await self.leased(session, row.id, row.lease_token)
                if current is None:
                    return
                current.issue_number, current.issue_id, current.issue_url = (
                    issue["number"],
                    issue["id"],
                    issue["html_url"],
                )
            row.issue_number, row.issue_id, row.issue_url = issue["number"], issue["id"], issue["html_url"]
        await github.write(
            "PATCH",
            f"{root}/issues/{row.issue_number}",
            {
                key: desired[key]
                for key in (
                    ("title", "body", "state", "state_reason")
                    if desired["state"] == "closed"
                    else ("title", "body", "state")
                )
            },
        )
        if desired["parent"]:
            async with AsyncTransaction() as session:
                parent = await session.scalar(
                    select(WorkIssueMirror).where(WorkIssueMirror.entity_id == UUID(desired["parent"]))
                )
            if parent is None or parent.issue_number is None:
                raise GitHubObservationError("Waiting for the parent issue record to synchronize")
            existing_parent = await github.optional(f"{root}/issues/{row.issue_number}/parent")
            if existing_parent is None or existing_parent.get("number") != parent.issue_number:
                await github.write(
                    "POST",
                    f"{root}/issues/{parent.issue_number}/sub_issues",
                    {
                        "sub_issue_id": row.issue_id,
                        "replace_parent": True,
                    },
                )
        async with AsyncTransaction() as session:
            current = await self.leased(session, row.id, row.lease_token)
            if current:
                current.synced_digest, current.error = row.digest, None
                # Refresh links as mappings become known; a newer local revision remains pending.
        async with AsyncTransaction() as session:
            saved_plan = await session.get(WorkPlan, plan.id, with_for_update=True)
            assert saved_plan is not None
            await refresh_mirrors(session, saved_plan)
