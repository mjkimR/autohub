#!/usr/bin/env bash
# Share module selection and tooling between fixing and read-only lint recipes.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"

backend_args=()
lint_args=()
format_args=(--check)
if [[ "${1:-}" == "--fix" ]]; then
    backend_args=(--fix)
    lint_args=(--fix)
    format_args=()
    shift
fi
target=$(resolve_module "${1:-all}")

if should_run "$target" "hub"; then
    bash scripts/check-backend.sh ${backend_args[@]+"${backend_args[@]}"} "$(resolve_module_path hub)"
fi

if should_run "$target" "sdk"; then
    uv run --no-active --no-sync devkit run -- uv run --no-active --no-sync ruff check ${lint_args[@]+"${lint_args[@]}"} --output-format=concise packages/sdk
    uv run --no-active --no-sync devkit run -- uv run --no-active --no-sync ruff format ${format_args[@]+"${format_args[@]}"} packages/sdk
fi

if should_run "$target" "hub-ui"; then
    activate_frontend_node
    if [[ "${lint_args[*]:-}" == "--fix" ]]; then
        uv run --no-active --no-sync devkit run -- npm --prefix "$(resolve_module_path hub-ui)" run format
        uv run --no-active --no-sync devkit run -- npm --prefix "$(resolve_module_path hub-ui)" run lint -- --fix
    else
        uv run --no-active --no-sync devkit run -- npm --prefix "$(resolve_module_path hub-ui)" run lint
    fi
fi
