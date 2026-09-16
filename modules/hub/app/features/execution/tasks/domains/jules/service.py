"""Scheduled Jules sessions: admitted by the AI catalog gateway, created through the Jules API, tracked to the end.

A session is either task work or a report. Task work converges on the pull request Jules opens, which the hub
adopts into the matching project's pipeline (CI, fixes through the project's catalog, merge). A report ends as the
session's final message, which the hub stores. Nothing else of a session's output is kept.
"""

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

SESSION_MARKER = "hub-session"
# Past this age an unconfirmed create that reconciliation cannot find is presumed lost.
UNCONFIRMED_SESSION_TIMEOUT = timedelta(hours=1)
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
            adoption: tuple[str | None, str | None] | None = None
            async with AsyncTransaction() as session:
                row = await session.get(AICatalogSession, session_id, with_for_update=True)
                if row is None or row.state in SESSION_TERMINAL_STATES:
                    continue
                if remote is not None:
                    self._apply(row, remote, now)
                    if row.state == "completed":
                        adoption = self._complete(row, final_message)
                elif now - utc(created_at) >= UNCONFIRMED_SESSION_TIMEOUT:
                    row.state = "failed"
                    row.failure_detail = "Jules never confirmed the session; its creation is presumed lost"
                    row.observed_at = now
            if adoption is not None:
                await self._adopt_pull_request(session_id, *adoption)

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
    def _complete(row: AICatalogSession, final_message: str | None) -> tuple[str | None, str | None] | None:
        """Record a completed session's deliverable; returns the pull request to adopt for task work."""
        row.result_summary = final_message
        if row.work_type != SESSION_WORK_TYPE_TASK:
            return None
        if row.pull_request_url is None:
            row.failure_detail = "Task session completed without opening a pull request"
            return None
        if row.pipeline_run_id is not None:
            return None
        return row.repository, row.pull_request_url

    async def _adopt_pull_request(self, session_id: UUID, repository: str | None, pull_request_url: str) -> None:
        """Enroll a task session's pull request into its project's pipeline as already implemented."""
        detail: str | None = None
        run_id: UUID | None = None
        match = PULL_REQUEST_URL.match(pull_request_url)
        if self.runs is None:
            detail = "Pull request adoption is not available in this context"
        elif match is None or (repository is not None and match["repository"].lower() != repository):
            detail = "Pull request is not in the session's repository"
        else:
            target = match["repository"].lower()
            async with AsyncTransaction() as session:
                project = await session.scalar(select(Project).where(Project.github_repository == target))
                project_id = project.id if project is not None else None
                adoptable = (
                    project is not None and project.enabled and project.automation.get("auto_enroll_sessions", True)
                )
            if project_id is None:
                detail = "No project is connected to the session's repository"
            elif not adoptable:
                detail = "The project does not adopt session pull requests"
            else:
                try:
                    run = await self.runs.enroll(
                        project_id, EnrollPullRequest(pull_number=int(match["number"]), implemented=True)
                    )
                    run_id = run.id
                except ProjectError as exc:
                    detail = f"Pull request was not adopted: {exc.detail}"
        async with AsyncTransaction() as session:
            row = await session.get(AICatalogSession, session_id, with_for_update=True)
            if row is None:
                return
            row.pipeline_run_id = run_id
            row.failure_detail = detail

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
        url = remote.get("url")
        if isinstance(url, str):
            row.url = url[:2048]
        for output in remote.get("outputs") or []:
            pull_request = output.get("pullRequest") if isinstance(output, dict) else None
            if isinstance(pull_request, dict) and isinstance(pull_request.get("url"), str):
                row.pull_request_url = pull_request["url"][:2048]
        row.observed_at = now
