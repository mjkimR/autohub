#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
if ! command -v apm >/dev/null 2>&1; then
    echo "Install Microsoft APM first: uv tool install apm-cli==0.30.0" >&2
    exit 1
fi
exec apm install --frozen "$@"
