"""Delivery capabilities without importing adapter implementations or persistence."""

CODEX_GITHUB_MENTION = "codex-github-mention"
PIPELINE_DELIVERY_ADAPTERS = frozenset({CODEX_GITHUB_MENTION})


def supports_pipeline_delivery(adapter: str) -> bool:
    return adapter in PIPELINE_DELIVERY_ADAPTERS
