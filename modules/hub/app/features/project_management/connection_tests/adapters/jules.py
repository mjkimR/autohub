"""Jules probes own their sessions; they never enter task-session PR adoption."""

import re
from typing import Literal
from uuid import UUID

from app.features.ai_catalogs.providers import jules as provider
from app.features.ai_catalogs.providers.jules import SESSION_NAME, JulesApiError, JulesClient
from app.features.project_management.connection_tests.adapters.base import TestContext
from app.features.project_management.connection_tests.adapters.jules_cleanup import cleanup_jules
from app.features.project_management.connection_tests.adapters.specs import JULES_SPEC
from app.features.project_management.connection_tests.github import ConnectionTestGitHub
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.connection_tests.ownership import marker
from app.features.project_management.pipelines.github import GitHubObservationError
from app_layer_base.utils.time_util import get_current_utc_time


class JulesSessionProbe:
    def __init__(self, client: JulesClient, github: ConnectionTestGitHub):
        self.client, self.github = client, github

    @staticmethod
    def title(row: ConnectionTest) -> str:
        return f"AutoHub connection test [hub-connection-test:{row.id}]"

    async def prepare(self, row: ConnectionTest) -> None:
        row.evidence["source_name"] = await self.client.resolve_source(row.repository)
        await self.github.prepare_branch(row)
        row.phase = "dispatching"

    async def dispatch(self, row: ConnectionTest, *, create_once: bool) -> None:
        if create_once:
            branch = self.github.branch(row)
            remote = await self.client.create_session(
                repository=row.repository,
                source_name=row.evidence["source_name"],
                starting_branch=branch,
                title=self.title(row),
                auto_create_pr=True,
                prompt=(
                    f"This is an isolated AutoHub connection test. Start from `{branch}`. "
                    f"Replace only `{self.github.fixture(row)}` with `verified:{row.id}` and a newline. "
                    "Follow AGENTS.md, run repository checks, commit the change and open one Draft PR "
                    f"targeting `{branch}`. Include `{marker(row)}` in the PR body. "
                    "Never merge, enable auto-merge, target the default branch, or change other files."
                ),
            )
        else:
            remote = await self.remote(row)
        if remote is not None:
            self.record(row, remote)
            row.phase = "waiting_for_session"
        else:
            row.detail = "Reconciling the original Jules create request; it will not be sent twice"

    async def remote(self, row: ConnectionTest) -> dict | None:
        name = row.evidence.get("session_name")
        return await self.client.get_session(name) if name else await self.client.find_session_by_title(self.title(row))

    @staticmethod
    def record(row: ConnectionTest, remote: dict) -> None:
        name = remote.get("name")
        if not isinstance(name, str) or not SESSION_NAME.fullmatch(name):
            raise JulesApiError("Jules returned an invalid session name")
        state = str(remote.get("state", "")).lower()
        row.evidence.update(session_name=name, session_state=state)
        row.evidence.setdefault("delivered_at", remote.get("createTime") or get_current_utc_time().isoformat())
        if state in ("completed", "failed"):
            row.evidence["execution_finished"] = True
        url = remote.get("url")
        if isinstance(url, str) and url.startswith("https://jules.google.com/"):
            row.evidence["session_url"] = url

    async def find_pull(self, row: ConnectionTest, remote: dict) -> bool:
        found = 0
        unresolved = False
        for output in remote.get("outputs") or []:
            url = (output.get("pullRequest") or {}).get("url", "")
            match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/pull/([0-9]+)/?", url)
            if not match or match[1].lower() != row.repository.lower():
                unresolved = unresolved or bool(url)
                continue
            number = int(match[2])
            pr = await self.github.reader._get(f"/repos/{row.repository}/pulls/{number}")
            head = pr.get("head") or {}
            if (head.get("repo") or {}).get("full_name", "").lower() != row.repository.lower():
                raise GitHubObservationError("Jules test returned a fork PR; inspect the session", 422)
            # Prove ownership before any close/delete, even if the provider returns an unrelated URL.
            comparison = await self.github.reader._get(
                f"/repos/{row.repository}/compare/{row.evidence['initial_sha']}...{head['sha']}"
            )
            if comparison.get("status") not in ("ahead", "identical"):
                raise GitHubObservationError("Jules PR is not descended from the isolated test branch", 422)
            self.github.record_owned_pull(row, pr, proof="provider_output")
            await self.github.mark_pull(row, pr)
            found += 1
            if pr["base"]["ref"] != self.github.branch(row):
                row.status, row.detail = "failed", "Jules PR targeted a different base; closing the test PR"
        if str(remote.get("state", "")).lower() in ("completed", "failed") and not unresolved:
            row.evidence["provider_output_confirmed"] = True
            if found:
                row.evidence["output_discovery_pending"] = False
        if found > 1:
            row.status, row.detail = "failed", "Jules returned multiple test PRs; closing all owned output"
        return found > 0

    async def observe(self, row: ConnectionTest) -> None:
        remote = await self.remote(row)
        if remote is None:
            return
        self.record(row, remote)
        found = await self.find_pull(row, remote)
        if row.status != "running":
            return
        state = row.evidence["session_state"]
        if state in ("failed", "awaiting_plan_approval", "awaiting_user_feedback", "paused"):
            row.status, row.detail = "failed", f"Jules session needs attention: {state}"
        elif state == "completed":
            if found:
                await self.github.observe(row, expected_branch=row.evidence["output_branch"])
            else:
                row.status, row.detail = "failed", "Jules completed without a test PR in this repository"


class JulesConnectionTestAdapter:
    """Credentials are needed for provider I/O, never as a prerequisite for GitHub cleanup."""

    spec = JULES_SPEC

    async def _run(
        self,
        row: ConnectionTest,
        context: TestContext,
        action: Literal["prepare", "dispatch", "observe", "reconcile"],
        *,
        create_once: bool = False,
    ) -> None:
        assert row.catalog_snapshot is not None
        api_key = await context.observer.get_token(UUID(row.catalog_snapshot["connector_id"]), "jules")
        async with provider.create_jules_client(api_key) as http:
            probe = JulesSessionProbe(provider.JulesClient(http), context.github)
            if action == "prepare":
                await probe.prepare(row)
            elif action == "dispatch":
                await probe.dispatch(row, create_once=create_once)
            elif action == "observe":
                await probe.observe(row)
            else:
                remote = await probe.remote(row)
                if remote:
                    probe.record(row, remote)
                    status, detail = row.status, row.detail
                    await probe.find_pull(row, remote)
                    row.status, row.detail = status, detail

    async def prepare(self, row: ConnectionTest, context: TestContext) -> None:
        await self._run(row, context, "prepare")

    async def dispatch(self, row: ConnectionTest, context: TestContext, *, create_once: bool) -> None:
        await self._run(row, context, "dispatch", create_once=create_once)

    async def observe(self, row: ConnectionTest, context: TestContext) -> None:
        await self._run(row, context, "observe")

    async def cleanup(self, row: ConnectionTest, context: TestContext) -> None:
        await cleanup_jules(row, context, lambda: self._run(row, context, "reconcile"))
