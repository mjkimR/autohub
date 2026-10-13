#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
exec uv run --no-active --no-sync devkit sync --preset advisory:core --preset advisory:python "$@"
