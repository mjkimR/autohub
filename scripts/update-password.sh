#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Change the operator's password: Secret Manager, then a Cloud Run restart.
#
# The hub keeps the account's password equal to FIRST_USER_PASSWORD on every start, so the bundle is the one
# place it is changed. The old password and the sessions issued under it stop working once the new revision
# serves. Cloud Scheduler is not involved: it holds a key of its own (a managed machine API key).
# ─────────────────────────────────────────────────────────────────────────────

PASSWORD="${1:-}"

if [[ -z "$PASSWORD" ]]; then
  read -rsp "Enter new password: " PASSWORD
  echo ""
fi

if [[ -z "$PASSWORD" ]]; then
  echo "Error: Password cannot be empty." >&2
  exit 1
fi

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-us-west1}"
SERVICE_NAME="${SERVICE_NAME:-autohub}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Error: GCP Project ID is required. Set via 'gcloud config set project <project>'." >&2
  exit 1
fi

echo "==> Changing the operator's password for project: $PROJECT_ID (Region: $REGION)"

# 1. Update Secret Manager
echo "==> [1/2] Updating Google Secret Manager ('autohub-secrets')..."
CURRENT_JSON=$(gcloud secrets versions access latest --secret=autohub-secrets --project="$PROJECT_ID" 2>/dev/null || true)
if [[ -z "$CURRENT_JSON" ]]; then
  echo "Error: autohub-secrets does not exist. Run 'just setup-secrets' first." >&2
  exit 1
fi
UPDATED_JSON=$(CURRENT_JSON="$CURRENT_JSON" PASSWORD="$PASSWORD" python3 -c 'import json, os; value=json.loads(os.environ["CURRENT_JSON"]); assert value.get("FIRST_USER_EMAIL"), "the bundle has no account yet; re-run just setup-secrets"; value["FIRST_USER_PASSWORD"]=os.environ["PASSWORD"]; value["FIRST_USER_SYNC_PASSWORD"]="true"; print(json.dumps(value, separators=(",", ":")))')
echo -n "$UPDATED_JSON" | gcloud secrets versions add "autohub-secrets" \
  --project="$PROJECT_ID" --data-file=- >/dev/null
echo "  ✓ Added new version to 'autohub-secrets'."

# 2. Restart Cloud Run so the new password is applied at startup
echo "==> [2/2] Updating Cloud Run service ('$SERVICE_NAME')..."
if gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud run services update "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --update-secrets="APP_SECRETS_JSON=autohub-secrets:latest" >/dev/null
  echo "  ✓ Deployed new revision; the password changes when it starts."
else
  echo "  - Notice: Cloud Run service '$SERVICE_NAME' not found in $REGION. (Run 'just deploy-cloud-run' to deploy it)"
fi

echo ""
echo "==> Password change complete. For local development, set FIRST_USER_PASSWORD in modules/hub/.env yourself."
