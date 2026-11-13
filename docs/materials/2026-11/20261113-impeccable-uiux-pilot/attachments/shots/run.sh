#!/usr/bin/env bash
# One-command capture: ./run.sh <label>   (e.g. before, after)
# Starts hub-ui `vite dev` with a dead backend proxy (no real API), captures, stops the server.
# Restore this directory outside the repository (for example a scratch folder) before running:
# npm ci writes node_modules/ and captures write out/ next to this script.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LABEL="${1:-after}"
# HUB_UI_DIR: the modules/hub-ui directory of the checkout or worktree under test (required).
UI="${HUB_UI_DIR:?set HUB_UI_DIR to <autohub checkout>/modules/hub-ui}"
PORT="${PORT:-5199}"
# NODE_BIN: optional directory prepended to PATH (the pilot used Node 24.18 from nvm).
if [ -n "${NODE_BIN:-}" ]; then export PATH="$NODE_BIN:$PATH"; fi
[ -d "$HERE/node_modules/playwright" ] || (cd "$HERE" && npm ci)
LOG="$HERE/vite-$LABEL.log"
# AUTO_HUB_SERVER points at a closed port so even an unintercepted request can never reach a real backend.
( cd "$UI" && AUTO_HUB_SERVER=http://127.0.0.1:9 exec ./node_modules/.bin/vite dev --port "$PORT" --strictPort --configLoader runner ) >"$LOG" 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null; wait $PID 2>/dev/null || true' EXIT
for _ in $(seq 1 60); do curl -sf "http://localhost:$PORT/" >/dev/null && break; sleep 1; done
curl -sf "http://localhost:$PORT/" >/dev/null || { echo "vite did not start; see $LOG"; exit 1; }
node "$HERE/capture.mjs" "$LABEL" "http://localhost:$PORT"
