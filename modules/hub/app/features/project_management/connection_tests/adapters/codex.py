"""Codex mention recipe, using the production quota-response classifier."""

from datetime import datetime, timedelta
from typing import Any

from app.features.project_management.connection_tests.adapters.base import TestContext
from app.features.project_management.connection_tests.adapters.specs import CODEX_SPEC
from app.features.project_management.connection_tests.models import ACTIVE, ConnectionTest
from app.features.project_management.pipeline_runs.dispatch import CODEX_CONNECTOR_LOGIN, is_codex_quota_reply
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.pipelines.github import GitHubObservationError
from app_layer_base.utils.time_util import get_current_utc_time

# Codex pushes before posting its final reply; allow GitHub ref reads to catch up before failing.
REPLY_PUSH_GRACE = timedelta(minutes=5)


class CodexConnectionTestAdapter:
    spec = CODEX_SPEC

    async def prepare(self, row: ConnectionTest, context: TestContext) -> None:
        user = await context.github.reader._get("/user")
        if user.get("type") != "User" or not user.get("login"):
            raise GitHubObservationError("Codex mention tests require a GitHub user PAT", 422)
        row.evidence["github_login"] = user["login"]
        await context.github.prepare_branch(row)
        await context.github.prepare_draft(row)

    async def dispatch(self, row: ConnectionTest, context: TestContext, *, create_once: bool) -> None:
        number = row.evidence["pull_number"]
        marker = f"<!-- hub-connection-test:{row.id} -->"
        login = await context.github.reader.current_login()
        if login != row.evidence["github_login"]:
            raise GitHubObservationError("Connector account changed; start a new connection test", 422)
        comment = await context.github.reader.reconcile_issue_comment(row.repository, number, marker, login)
        if comment is None:
            branch, fixture = context.github.branch(row), context.github.fixture(row)
            body = (
                f"@codex Run this AutoHub connection test on the existing PR branch `{branch}`.\n"
                f"Replace only `{fixture}` with the exact line `verified:{row.id}` followed by a newline.\n"
                "Follow AGENTS.md and run the repository checks. Commit that change and push to this same branch.\n"
                "Keep this PR draft. Never merge, mark ready, create another PR, or modify other files.\n"
                "Use the environment's GH_TOKEN and network access to github.com to push:\n"
                f'git push "https://x-access-token:${{GH_TOKEN}}@github.com/{row.repository}.git" HEAD:{branch}\n'
                f"After pushing, verify the remote head with git ls-remote.\n\n{marker}"
            )
            comment = await context.github.reader.post_issue_comment(row.repository, number, body)
        row.evidence.update(comment_id=comment["id"], comment_url=comment.get("html_url"))
        row.evidence["delivered_at"] = comment.get("created_at") or get_current_utc_time().isoformat()
        row.phase = "waiting_for_push"

    async def observe(self, row: ConnectionTest, context: TestContext) -> None:
        reply = await self.final_reply(row, context)
        if reply is not None:
            row.evidence["reply_url"] = reply.get("html_url")
            # The cloud task has ended once Codex replies, so it no longer holds catalog capacity.
            row.evidence["execution_finished"] = True
            row.evidence.setdefault("reply_observed_at", get_current_utc_time().isoformat())
            if is_codex_quota_reply(CODEX_CONNECTOR_LOGIN, reply.get("body")):
                row.evidence["quota_observed_at"] = reply.get("created_at") or get_current_utc_time().isoformat()
                row.status, row.detail = (
                    "failed",
                    "Codex reported its usage limit; the catalog will wait for quota recovery",
                )
                return
        await context.github.observe(row, expected_branch=context.github.branch(row))
        if row.evidence.get("verified_sha"):
            row.evidence["execution_finished"] = True
        elif (
            reply is not None
            and row.status == ACTIVE
            and get_current_utc_time()
            >= as_utc(datetime.fromisoformat(row.evidence["reply_observed_at"])) + REPLY_PUSH_GRACE
        ):
            row.status, row.detail = (
                "failed",
                "Codex replied without pushing the test change; read its reply and check the environment GH_TOKEN",
            )

    async def final_reply(self, row: ConnectionTest, context: TestContext) -> dict[str, Any] | None:
        """Return Codex's first reply after the test mention, which it posts when its cloud task ends."""
        comments = await context.github.reader.list_issue_comments(row.repository, row.evidence["pull_number"])
        for comment in comments:
            author = comment.get("user", {}).get("login", "").removesuffix("[bot]")
            if comment.get("id", 0) > row.evidence.get("comment_id", 0) and author == CODEX_CONNECTOR_LOGIN:
                return comment
        return None

    async def cleanup(self, row: ConnectionTest, context: TestContext) -> None:
        # A canceled or failed test stops observing; still release capacity once Codex has replied.
        if row.evidence.get("comment_id") and not row.evidence.get("execution_finished"):
            reply = await self.final_reply(row, context)
            if reply is not None:
                row.evidence.update(reply_url=reply.get("html_url"), execution_finished=True)
        await context.github.cleanup(row)
