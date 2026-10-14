#!/usr/bin/env bash
set -euo pipefail
runtime=$(cd "${1:?runtime directory required}" && pwd -P)
export AUTOHUB_SDD_HOME="$runtime"
export AUTOHUB_REQUIRE_SDD=1
test -x "$runtime/.venv/bin/devkit" && test -f "$runtime/pin.json" || { echo 'Run just install-sdd first' >&2; exit 1; }
just test tests/integration/features/project_management/sdd tests/integration/features/execution/flows/test_bridge.py
