"""Scheduled Jules sessions: admitted by the AI catalog gateway, created through the Jules API, tracked to the end.

A session is either task work or a report. Task work converges on the pull request Jules opens, which the hub
adopts into the matching project's pipeline (CI, fixes through the project's catalog, merge). A report ends as the
session's final message, which the hub stores. Nothing else of a session's output is kept.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from app.features.ai_catalogs.models import (
    SESSION_DISPATCHING,
    SESSION_TERMINAL_STATES,
    SESSION_WORK_TYPE_REPORT,
    SESSION_WORK_TYPE_TASK,
    AICatalogKind,
    AICatalogSession,
)
from app.features.ai_catalogs.policies.base import utc
from app.features.ai_catalogs.services import CATALOG_CONNECTOR_PROVIDERS, AICatalogService
from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, EncryptedCredentials
from app.features.configuration.connectors.models import Connector
from app.features.execution.tasks.domains.jules.client import (
    SESSION_NAME,
    JulesApiError,
    JulesClient,
    create_jules_client,
)
from app.features.project_management.pipeline_runs.schemas import EnrollPullRequest
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.projects.models import Project
from app.features.project_management.projects.services import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

logger = logging.getLogger(__name__)

SESSION_MARKER = "hub-session"
# Past this age an unconfirmed create that reconciliation cannot find is presumed lost.
UNCONFIRMED_SESSION_TIMEOUT = timedelta(hours=1)
# Jules states that wait for a person to answer. Nobody answers a scheduled session, so they are failed at once
# instead of holding the catalog's concurrency for good.
STALLED_STATES = ("awaiting_plan_approval", "awaiting_user_feedback", "paused")
PULL_REQUEST_URL = re.compile(r"^https://github\.com/(?P<repository>[^/]+/[^/]+)/pull/(?P<number>\d+)(?:[/?#].*)?$")
REPORT_DELIVERY_INSTRUCTIONS = (
    "Deliver the full report as your final message in this session. Do not create branches, commits, or "
    "pull requests; the report is read from the session itself."
)
TASK_DELIVERY_INSTRUCTIONS = (
    "Commit your changes and open one pull request from a new branch; the hub adopts it. Do not push to an "
    "existing pull request branch. Finish with a short summary of what the pull request changes."
)


class JulesSessionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_key: str = Field(default="personal-jules", min_length=1, max_length=100)
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", description="GitHub owner/repo")
    starting_branch: str = Field(default="main", min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=20_000)
    work_type: Literal["task", "report"] = Field(
        default=SESSION_WORK_TYPE_TASK,
        description="'task' work ends in a pull request the hub adopts into the pipeline; a 'report' ends as the "
        "session's final message, which the hub stores",
    )
    auto_create_pr: bool | None = Field(
        default=None,
        description="Let Jules open a pull request with its changes; defaults to true for task work, false for reports",
    )

    @model_validator(mode="after")
    def _default_pull_request_mode(self) -> "JulesSessionPayload":
        if self.auto_create_pr is None:
            self.auto_create_pr = self.work_type == SESSION_WORK_TYPE_TASK
        elif self.auto_create_pr and self.work_type == SESSION_WORK_TYPE_REPORT:
            raise ValueError("A report session cannot open a pull request; its deliverable is the final message")
        return self

    @property
    def session_prompt(self) -> str:
        """The operator's prompt plus the delivery contract of its work type."""
        contract = (
            REPORT_DELIVERY_INSTRUCTIONS if self.work_type == SESSION_WORK_TYPE_REPORT else TASK_DELIVERY_INSTRUCTIONS
        )
        return f"{self.prompt.rstrip()}\n\n{contract}"


class JulesSyncPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_key: str = Field(default="personal-jules", min_length=1, max_length=100)


class JulesSessionService:
    def __init__(
        self,
        catalogs: AICatalogService,
        cipher: ConnectorCredentialCipher,
        runs: PipelineRunUseCase | None = None,
    ) -> None:
        self.catalogs = catalogs
        self.cipher = cipher
        # Adopts task sessions' pull requests; without it, completed task sessions only record their link.
        self.runs = runs

    async def start(self, payload: JulesSessionPayload, schedule_config_id: UUID | None) -> UUID:
        """Refresh tracked sessions, then start one new session if the catalog admits it."""
        catalog_id, api_key = await self._catalog_access(payload.catalog_key)
        async with create_jules_client(api_key) as http:
            client = JulesClient(http)
            await self._observe(client, catalog_id)
            session_id = uuid4()
            title = f"{payload.title} [{SESSION_MARKER}:{session_id}]"
            async with AsyncTransaction() as session:
                admission = await self.catalogs.request_dispatch(
                    session, catalog_id, None, f"session:{session_id}", get_current_utc_time()
                )
                if admission.rejection is None:
                    session.add(
                        AICatalogSession(
                            id=session_id,
                            ai_catalog_id=catalog_id,
                            schedule_config_id=schedule_config_id,
                            title=title,
                            work_type=payload.work_type,
                            repository=payload.repository.lower(),
                            state=SESSION_DISPATCHING,
                        )
                    )
            # Leave the transaction successfully so policy holds survive a rejected admission.
            if admission.rejection is not None:
                raise ProjectError(409, admission.rejection)
            try:
                remote = await client.create_session(
                    repository=payload.repository,
                    starting_branch=payload.starting_branch,
                    prompt=payload.session_prompt,
                    title=title,
                    auto_create_pr=bool(payload.auto_create_pr),
                )
            except JulesApiError as exc:
                await self._record_create_failure(session_id, catalog_id, exc)
                raise ProjectError(exc.status_code if exc.status_code in (422, 429) else 502, str(exc)) from None
            async with AsyncTransaction() as session:
                row = await session.get(AICatalogSession, session_id, with_for_update=True)
                if row is not None:
                    self._apply(row, remote, get_current_utc_time())
        return session_id

    async def sync(self, catalog_key: str) -> None:
        """Refresh unfinished sessions so finished ones release catalog concurrency and deliver their results."""
        catalog_id, api_key = await self._catalog_access(catalog_key)
        async with create_jules_client(api_key) as http:
            await self._observe(JulesClient(http), catalog_id)

    async def _catalog_access(self, catalog_key: str) -> tuple[UUID, str]:
        async with AsyncTransaction() as session:
            catalog = await self.catalogs.repo.get_by_key(session, catalog_key)
            if catalog is None or catalog.kind != AICatalogKind.JULES:
                raise ProjectError(422, f"'{catalog_key}' is not a Jules AI catalog")
            if catalog.connector_id is None:
                raise ProjectError(422, "Assign a Jules connector to the catalog before starting sessions")
            connector = await session.get(Connector, catalog.connector_id)
            provider = CATALOG_CONNECTOR_PROVIDERS[AICatalogKind.JULES]
            if connector is None or not connector.enabled or connector.provider != provider:
                raise ProjectError(422, "The catalog's Jules connector is missing, disabled, or of another provider")
            catalog_id, connector_id = catalog.id, connector.id
            encrypted = EncryptedCredentials(
                ciphertext=connector.credentials_ciphertext,
                nonce=connector.credentials_nonce,
                key_version=connector.credential_key_version,
            )
        credentials = await self.cipher.decrypt(connector_id, provider, encrypted)
        api_key = credentials.get("token")
        if not isinstance(api_key, str) or not api_key.strip():
            raise ProjectError(422, "The Jules connector's credentials must hold the API key as token")
        return catalog_id, api_key

    async def _observe(self, client: JulesClient, catalog_id: UUID) -> None:
        async with AsyncTransaction() as session:
            tracked = [
                (row.id, row.external_name, row.title, row.created_at)
                for row in await self.catalogs.repo.list_unfinished_sessions(session, catalog_id)
            ]
        for session_id, name, title, created_at in tracked:
            try:
                remote = await client.get_session(name) if name else await client.find_session_by_title(title)
            except JulesApiError:
                # Observation retries on the next run; it never blocks starting new work.
                continue
            final_message = await self._final_message(client, remote)
            now = get_current_utc_time()
            async with AsyncTransaction() as session:
                row = await session.get(AICatalogSession, session_id, with_for_update=True)
                if row is None or row.state in SESSION_TERMINAL_STATES:
                    continue
                if remote is not None:
                    self._apply(row, remote, now)
                    if row.state == "completed":
                        self._complete(row, final_message)
                elif now - utc(created_at) >= UNCONFIRMED_SESSION_TIMEOUT:
                    row.state = "failed"
                    row.failure_detail = "Jules never confirmed the session; its creation is presumed lost"
                    row.observed_at = now
        # Adoption is a separate pass over every completed task session that still has neither a run nor a
        # verdict, so a crash or an unexpected error after completion is retried on the next sync.
        async with AsyncTransaction() as session:
            pending = [
                (row.id, row.repository, row.pull_request_url)
                for row in await self.catalogs.repo.list_sessions_awaiting_adoption(session, catalog_id)
                if row.pull_request_url is not None
            ]
        for session_id, repository, pull_request_url in pending:
            await self._adopt_pull_request(session_id, repository, pull_request_url)

    @staticmethod
    async def _final_message(client: JulesClient, remote: dict[str, Any] | None) -> str | None:
        """Read a completing session's final message; a failed read leaves the summary empty rather than retrying."""
        if remote is None or str(remote.get("state", "")).lower() != "completed":
            return None
        name = remote.get("name")
        if not isinstance(name, str) or not SESSION_NAME.fullmatch(name):
            return None
        try:
            return await client.final_agent_message(name)
        except JulesApiError:
            return None

    @staticmethod
    def _complete(row: AICatalogSession, final_message: str | None) -> None:
        """Record a completed session's deliverable. A task session's pull request is adopted in a later pass."""
        row.result_summary = final_message
        if row.work_type == SESSION_WORK_TYPE_TASK and row.pull_request_url is None:
            row.failure_detail = "Task session completed without opening a pull request"

    async def _adopt_pull_request(self, session_id: UUID, repository: str | None, pull_request_url: str) -> None:
        """Enroll a task session's pull request into its project's pipeline as already implemented.

        Every outcome is written to the session, so one bad adoption never stops the sync and is never retried
        blindly; only a crash before the write leaves the session for the next pass.
        """
        detail: str | None = None
        run_id: UUID | None = None
        try:
            run_id, detail = await self._enroll_pull_request(repository, pull_request_url)
        except Exception as exc:  # The verdict must reach the row whatever failed.
            logger.exception("Adopting the pull request of Jules session %s failed", session_id)
            detail = f"Pull request adoption failed: {exc}"
        async with AsyncTransaction() as session:
            row = await session.get(AICatalogSession, session_id, with_for_update=True)
            if row is None:
                return
            row.pipeline_run_id = run_id
            row.failure_detail = detail

    async def _enroll_pull_request(
        self, repository: str | None, pull_request_url: str
    ) -> tuple[UUID | None, str | None]:
        """The adopted run's id, or the reason there is none."""
        match = PULL_REQUEST_URL.match(pull_request_url)
        if self.runs is None:
            return None, "Pull request adoption is not available in this context"
        if match is None or (repository is not None and match["repository"].lower() != repository):
            return None, "Pull request is not in the session's repository"
        target = match["repository"].lower()
        async with AsyncTransaction() as session:
            project = await session.scalar(select(Project).where(Project.github_repository == target))
            project_id = project.id if project is not None else None
            adoptable = project is not None and project.enabled and project.automation.get("auto_enroll_sessions", True)
        if project_id is None:
            return None, "No project is connected to the session's repository"
        if not adoptable:
            return None, "The project does not adopt session pull requests"
        pull_number = int(match["number"])
        try:
            run = await self.runs.enroll(project_id, EnrollPullRequest(pull_number=pull_number, implemented=True))
        except ProjectError as exc:
            # Somebody enrolled the pull request first (a comment trigger, the API); that run is the session's.
            async with AsyncTransaction() as session:
                existing = await self.runs.repo.get_active_for_pull(session, project_id, pull_number)
                existing_id = existing.id if existing is not None else None
            if existing_id is not None:
                return existing_id, None
            return None, f"Pull request was not adopted: {exc.detail}"
        return run.id, None

    async def _record_create_failure(self, session_id: UUID, catalog_id: UUID, exc: JulesApiError) -> None:
        if exc.status_code is None or exc.status_code >= 500:
            # The session may still have been created; title reconciliation settles it on a later run.
            return
        async with AsyncTransaction() as session:
            row = await session.get(AICatalogSession, session_id, with_for_update=True)
            if row is not None:
                row.state = "failed"
                row.failure_detail = str(exc)
            if exc.status_code == 429:
                # Jules does not document its limit error; a 429 is treated as its task cap being reached.
                await self.catalogs.record_quota_event(session, catalog_id, get_current_utc_time())

    @staticmethod
    def _apply(row: AICatalogSession, remote: dict[str, Any], now: datetime) -> None:
        name = remote.get("name")
        if isinstance(name, str) and SESSION_NAME.fullmatch(name):
            row.external_name = name
        state = remote.get("state")
        if isinstance(state, str) and state:
            row.state = state.lower()[:40]
            if row.state in STALLED_STATES:
                row.failure_detail = f"Jules is waiting for input the hub cannot give (session state: {row.state})"
                row.state = "failed"
        url = remote.get("url")
        if isinstance(url, str):
            row.url = url[:2048]
        for output in remote.get("outputs") or []:
            pull_request = output.get("pullRequest") if isinstance(output, dict) else None
            if isinstance(pull_request, dict) and isinstance(pull_request.get("url"), str):
                row.pull_request_url = pull_request["url"][:2048]
        row.observed_at = now
