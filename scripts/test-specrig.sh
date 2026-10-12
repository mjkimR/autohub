#!/usr/bin/env bash
set -euo pipefail
runtime=$(cd "${1:?runtime directory required}" && pwd -P)
export AUTOHUB_SPECRIG_HOME="$runtime"
export AUTOHUB_REQUIRE_SPECRIG=1
export PATH="$runtime/bin:$PATH"
test -x "$runtime/bin/specrig" && test -f "$runtime/pin.json" || { echo 'Run just install-specrig first' >&2; exit 1; }
just test tests/integration/features/project_management/specrig tests/integration/features/execution/flows/test_bridge.py
