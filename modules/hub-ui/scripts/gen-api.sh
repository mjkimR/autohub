#!/usr/bin/env sh
# Export backend OpenAPI and generate or check tag-based frontend declarations.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
case "${1:-write}" in write|--check) ;; *) echo "usage: gen-api.sh [--check]" >&2; exit 2 ;; esac
api_tmp="$(mktemp -d)"
trap 'rm -rf "$api_tmp"' EXIT HUP INT TERM
PYTHONPATH="$repo/modules/hub" uv run --no-active --project "$repo" python "$here/export-openapi.py" > "$api_tmp/openapi.json"
cd "$here/.."
if [ "${1:-write}" = "--check" ]; then
  npx --no-install app-common-gen-api --input "$api_tmp/openapi.json" --output src/lib/api/generated --default-non-nullable --check
else
  npx --no-install app-common-gen-api --input "$api_tmp/openapi.json" --output src/lib/api/generated --default-non-nullable
fi
