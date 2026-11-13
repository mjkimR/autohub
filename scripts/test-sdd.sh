#!/usr/bin/env bash
set -euo pipefail
case "${2:-sqlite}" in
    sqlite) test_recipe=test ;;
    postgres) test_recipe=test-pg ;;
    *) echo 'Database must be sqlite or postgres' >&2; exit 2 ;;
esac
runtime=$(cd "${1:?seed runtime directory required}" && pwd -P)
test -x "$runtime/.venv/bin/devkit" && test -f "$runtime/pin.json" || { echo 'Run just install-sdd first' >&2; exit 1; }
build="${AUTOHUB_SDD_BUILD:-$(pwd -P)/.cache/sdd-build}"
test -x "$build/.venv/bin/python" || { echo 'Run just install-sdd .cache/sdd-build config/sdd-build first' >&2; exit 1; }
# Fixture repositories lock config/sdd-runtime; the seed venv fills the cache entry for that lock's identity.
export AUTOHUB_TEST_SDD_SEED="$runtime"
export AUTOHUB_SDD_BUILD="$build"
export AUTOHUB_SDD_CACHE="${AUTOHUB_SDD_CACHE:-$(pwd -P)/.cache/sdd-test-runtimes}"
export AUTOHUB_REQUIRE_SDD=1
just "$test_recipe" tests/integration/features/project_management/sdd tests/integration/features/execution/flows/test_bridge.py
