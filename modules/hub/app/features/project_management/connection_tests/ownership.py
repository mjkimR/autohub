"""Positive ownership permits cleanup; ancestry alone only permits quarantine."""

import re

from app.features.project_management.connection_tests.models import ConnectionTest

TEST_LABEL = "autohub-connection-test"
OWNERSHIP_PROOFS = {"provider_output", "marker", "reserved_branch"}


def marker(row: ConnectionTest) -> str:
    return f"<!-- autohub-connection-test:{row.id} -->"


def has_marker(row: ConnectionTest, pr: dict) -> bool:
    return bool(
        re.search(
            rf"(?<![\w-])(?:auto)?hub-connection-test:{row.id}(?![\w-])",
            f"{pr.get('title', '')}\n{pr.get('body', '')}",
        )
    )


def confirmed(row: ConnectionTest, number: int | str) -> bool:
    return row.evidence.get("owned_pulls", {}).get(str(number), {}).get("proof") in OWNERSHIP_PROOFS


def quarantine(row: ConnectionTest, pr: dict) -> None:
    number = str(pr["number"])
    dismissed = row.evidence.get("cleanup_resolution", {}).get("unrelated_pulls", {})
    if dismissed.get(number) == pr["head"]["sha"]:
        row.evidence.get("unconfirmed_pulls", {}).pop(number, None)
        return
    row.evidence.setdefault("unconfirmed_pulls", {})[number] = {
        "branch": pr["head"]["ref"],
        "sha": pr["head"]["sha"],
        "url": pr["html_url"],
    }


def candidate_heads(row: ConnectionTest) -> dict[str, str]:
    return {number: pull["sha"] for number, pull in row.evidence.get("unconfirmed_pulls", {}).items()}
