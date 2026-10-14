#!/usr/bin/env bash
# Preserve the format, lint, and architecture checks behind the public just recipes.
set -euo pipefail

fix=false
if [[ "${1:-}" == "--fix" ]]; then
    fix=true
    shift
fi
backend_path=${1:-modules/hub}
format_args=(--check)
lint_args=()
if "$fix"; then
    format_args=()
    lint_args=(--fix)
fi
uv run --no-active --no-sync devkit run -- uv run --no-active --no-sync ruff format ${format_args[@]+"${format_args[@]}"} "$backend_path"
uv run --no-active --no-sync devkit run -- uv run --no-active --no-sync ruff check --output-format=concise ${lint_args[@]+"${lint_args[@]}"} "$backend_path"
# Only the fixing run redeploys the bundles; the check run reports drift without writing.
if "$fix"; then
    uv run --no-active --no-sync devkit sync
fi
uv run --no-active --no-sync devkit sync --check
uv run --no-active --no-sync devkit run -- uv run --no-active --no-sync devkit rules check "$backend_path"
