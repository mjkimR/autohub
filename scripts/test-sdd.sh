#!/usr/bin/env bash
set -euo pipefail
case "${2:-sqlite}" in
    sqlite) test_recipe=test ;;
    postgres) test_recipe=test-pg ;;
    *) echo 'Database must be sqlite or postgres' >&2; exit 2 ;;
esac
runtime=$(cd "${1:?runtime directory required}" && pwd -P)
export AUTOHUB_SDD_HOME="$runtime"
export AUTOHUB_REQUIRE_SDD=1
# The contract suite also proves that app-common projects select a different reviewed runtime.
if [[ -z "${AUTOHUB_TEST_SDD_APP_COMMON:-}" ]]; then
    export AUTOHUB_TEST_SDD_APP_COMMON="$(pwd -P)/.cache/sdd-app-common"
fi
test -f "$AUTOHUB_TEST_SDD_APP_COMMON/pin.json" || { echo 'Run just install-sdd .cache/sdd-app-common config/sdd-runtime-app-common first' >&2; exit 1; }
test -x "$runtime/.venv/bin/devkit" && test -f "$runtime/pin.json" || { echo 'Run just install-sdd first' >&2; exit 1; }
just "$test_recipe" tests/integration/features/project_management/sdd tests/integration/features/execution/flows/test_bridge.py
