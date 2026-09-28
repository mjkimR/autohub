#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Sign in to a hub as a human account and print a short-lived access token.
#
# Meant for ad-hoc API calls and live canaries (curl, httpie, scripts) without pasting a password into a
# shell history or a chat transcript. The password is read from AUTOHUB_PASSWORD or prompted without echo.
# Only the access token is printed by default; it expires in about 10 minutes. Use --json to also get the
# refresh token, or --out FILE to write the token there (mode 600) instead of stdout.
#
# Usage:
#   scripts/login-token.sh [--url URL] [--email EMAIL] [--out FILE] [--json]
#   AUTOHUB_URL, AUTOHUB_EMAIL, AUTOHUB_PASSWORD provide defaults. URL defaults to http://localhost:8000.
# ─────────────────────────────────────────────────────────────────────────────

URL="${AUTOHUB_URL:-http://localhost:8000}"
EMAIL="${AUTOHUB_EMAIL:-}"
OUT=""
FORMAT="token"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) URL="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --json) FORMAT="json"; shift ;;
    -h|--help) sed -n '4,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$EMAIL" ]]; then
  read -rp "Email: " EMAIL
fi
PASSWORD="${AUTOHUB_PASSWORD:-}"
if [[ -z "$PASSWORD" ]]; then
  read -rsp "Password for $EMAIL: " PASSWORD
  echo "" >&2
fi
if [[ -z "$EMAIL" || -z "$PASSWORD" ]]; then
  echo "Error: email and password are required." >&2
  exit 1
fi

RESPONSE_FILE="$(mktemp)"
trap 'rm -f "$RESPONSE_FILE"' EXIT
STATUS="$(curl -sS -m 30 -X POST "${URL%/}/api/v1/users/login/" \
  --data-urlencode "username=$EMAIL" --data-urlencode "password=$PASSWORD" \
  -o "$RESPONSE_FILE" -w '%{http_code}')"
unset PASSWORD

if [[ "$STATUS" != "200" ]]; then
  echo "Error: login failed with HTTP $STATUS" >&2
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("detail", ""), file=sys.stderr)' "$RESPONSE_FILE" 2>/dev/null || true
  exit 1
fi

if [[ "$FORMAT" == "json" ]]; then
  RESULT="$(cat "$RESPONSE_FILE")"
else
  RESULT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["access_token"])' "$RESPONSE_FILE")"
fi

if [[ -n "$OUT" ]]; then
  (umask 077; printf '%s' "$RESULT" > "$OUT")
  echo "Wrote ${FORMAT} to $OUT (access token expires in about 10 minutes)." >&2
else
  printf '%s\n' "$RESULT"
fi
