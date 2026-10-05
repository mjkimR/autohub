#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_lib.sh"

ui_path=$(resolve_module_path "hub-ui")

echo "Running frontend API contract command..."
activate_frontend_node
npm --prefix "$ui_path" run gen:api -- "$@"
echo "Frontend API contract command completed."
