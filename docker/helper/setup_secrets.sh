#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Setup Google Secret Manager secrets for Auto Hub
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-us-west1}"
DB_CONNECTION_NAME="${DB_CONNECTION_NAME:-}"
DB_USER="${DB_USER:-hub_user}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-auto_hub}"
DATABASE_URL="${DATABASE_URL:-}"
SA_NAME="${SA_NAME:-autohub-sa}"
RAW_APP_SECRET="${APP_SECRET:-${APP_SECRET_KEY:-}}"

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Set up Secret Manager secrets required by Auto Hub.

Options:
  -p, --project PROJECT_ID     GCP Project ID (default: current gcloud project)
  -r, --region REGION          GCP Region (default: us-west1)
  -s, --app-secret SECRET      Plaintext App Secret Key (will be SHA-256 hashed before storing)
  -a, --service-account NAME   Dedicated Service Account name (default: autohub-sa)
  -b, --database-url URL       Full PostgreSQL connection URL (e.g. Aiven/external DB)
  -c, --connection-name NAME   Cloud SQL Connection Name (PROJECT:REGION:INSTANCE)
  -u, --db-user USER           Database username (default: hub_user, for Cloud SQL)
  -w, --db-password PASSWORD   Database password (for Cloud SQL)
  -d, --db-name DBNAME         Database name (default: auto_hub)
  -h, --help                   Show this help message

Environment variables PROJECT_ID, REGION, APP_SECRET, DATABASE_URL, DB_CONNECTION_NAME, SA_NAME can also be used.
EOF
  exit 0
}



while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--project) PROJECT_ID="$2"; shift 2 ;;
    -r|--region) REGION="$2"; shift 2 ;;
    -s|--app-secret) RAW_APP_SECRET="$2"; shift 2 ;;
    -a|--service-account) SA_NAME="$2"; shift 2 ;;
    -b|--database-url) DATABASE_URL="$2"; shift 2 ;;
    -c|--connection-name) DB_CONNECTION_NAME="$2"; shift 2 ;;
    -u|--db-user) DB_USER="$2"; shift 2 ;;
    -w|--db-password) DB_PASSWORD="$2"; shift 2 ;;
    -d|--db-name) DB_NAME="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done


if [[ -z "$PROJECT_ID" ]]; then
  echo "Error: GCP Project ID is required. Set via -p <project> or 'gcloud config set project <project>'." >&2
  exit 1
fi

echo "==> Configuring Secret Manager in project: $PROJECT_ID"

# Enable Secret Manager and IAM API if not enabled
gcloud services enable secretmanager.googleapis.com iam.googleapis.com --project="$PROJECT_ID"

# Helper function to compute SHA-256 hash
hash_sha256() {
  local val="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    echo -n "$val" | sha256sum | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then
    echo -n "$val" | openssl dgst -sha256 | awk '{print $NF}'
  else
    python3 -c "import hashlib, sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())" "$val"
  fi
}

# Helper function to create secret if it does not exist, or add version if empty/forced
create_or_update_secret() {
  local secret_name="$1"
  local secret_val="$2"
  local force="${3:-false}"

  if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" >/dev/null 2>&1; then
    if [[ "$force" == "true" ]]; then
      echo "  - Updating secret '$secret_name' with new version..."
      echo -n "$secret_val" | gcloud secrets versions add "$secret_name" \
        --project="$PROJECT_ID" \
        --data-file=- >/dev/null
    else
      echo "  - Secret '$secret_name' already exists. Keeping existing secret."
    fi
  else
    echo "  - Creating secret '$secret_name'..."
    echo -n "$secret_val" | gcloud secrets create "$secret_name" \
      --project="$PROJECT_ID" \
      --replication-policy=automatic \
      --data-file=-
  fi
}

# Build one per-repository JSON bundle. Individual values never need their own
# Secret Manager resources; app-common expands this bundle at process startup.
#
# A re-run keeps every value the bundle already holds unless an option replaces it. Generated values are
# never regenerated: a new connector credential key makes every stored connector credential undecryptable,
# and a new webhook secret invalidates the webhooks already registered on GitHub.
EXISTING_JSON=""
if gcloud secrets describe "autohub-secrets" --project="$PROJECT_ID" >/dev/null 2>&1; then
  if ! EXISTING_JSON=$(gcloud secrets versions access latest --secret="autohub-secrets" --project="$PROJECT_ID" 2>/dev/null); then
    echo "Error: 'autohub-secrets' exists but its latest version cannot be read." >&2
    echo "       Refusing to regenerate its keys. Fix access, or delete the secret if it holds nothing worth keeping." >&2
    exit 1
  fi
  echo "  - Existing secret bundle found. Keeping its values unless an option replaces them."
fi

existing_value() {
  EXISTING_JSON="$EXISTING_JSON" python3 -c 'import json, os, sys; raw = os.environ["EXISTING_JSON"]; print((json.loads(raw) if raw else {}).get(sys.argv[1]) or "", end="")' "$1"
}

# 1. App secret (SHA-256 hashed secret for UI/API authentication)
LOGIN_KEY=""
if [[ -n "$RAW_APP_SECRET" ]]; then
  LOGIN_KEY="$RAW_APP_SECRET"
  echo "  - Plaintext App Secret provided. Computing SHA-256 hash..."
  APP_SECRET_VAL=$(hash_sha256 "$RAW_APP_SECRET")
  if [[ -n "$EXISTING_JSON" && "$APP_SECRET_VAL" != "$(existing_value APP_SECRET_KEY)" ]]; then
    echo "  - Notice: this replaces the API key in the bundle only. Cloud Scheduler and Cloud Run keep the old key;" >&2
    echo "            use 'just update-api-key' to rotate it everywhere at once." >&2
  fi
else
  APP_SECRET_VAL=$(existing_value APP_SECRET_KEY)
  if [[ -z "$APP_SECRET_VAL" ]]; then
    LOGIN_KEY=$(openssl rand -hex 32)
    APP_SECRET_VAL=$(hash_sha256 "$LOGIN_KEY")
  fi
fi

# 2. GitHub webhook secret (20 bytes hex)
WEBHOOK_SECRET_VAL=$(existing_value GITHUB_WEBHOOK_SECRET)
if [[ -z "$WEBHOOK_SECRET_VAL" ]]; then
  WEBHOOK_SECRET_VAL=$(openssl rand -hex 20)
fi

# 3. Database URL
if [[ -n "$DATABASE_URL" ]]; then
  # Normalize postgres://, postgresql://, or postgresql+asyncpg:// to postgresql+psycopg://
  if [[ "$DATABASE_URL" =~ ^postgres:// ]]; then
    DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgres://}"
  elif [[ "$DATABASE_URL" =~ ^postgresql:// ]]; then
    DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgresql://}"
  elif [[ "$DATABASE_URL" =~ ^postgresql\+asyncpg:// ]]; then
    DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgresql+asyncpg://}"
  fi
  echo "  - Storing provided DATABASE_URL..."
elif [[ -n "$DB_CONNECTION_NAME" ]]; then
  if [[ -z "$DB_PASSWORD" ]]; then
    read -rsp "Enter password for database user '$DB_USER': " DB_PASSWORD
    echo ""
  fi
  DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${DB_CONNECTION_NAME}"
else
  DATABASE_URL=$(existing_value DATABASE_URL)
  if [[ -z "$DATABASE_URL" ]]; then
    echo "Error: --database-url or --connection-name is required for the Auto Hub secret bundle." >&2
    exit 1
  fi
  echo "  - Keeping existing DATABASE_URL."
fi

# 4. Connector credential encryption key (base64-encoded 32-byte AES key)
CONNECTOR_KEY_VAL=$(existing_value CONNECTOR_CREDENTIAL_KEY)
CONNECTOR_KEY_VERSION=$(existing_value CONNECTOR_CREDENTIAL_KEY_VERSION)
if [[ -z "$CONNECTOR_KEY_VAL" ]]; then
  CONNECTOR_KEY_VAL=$(openssl rand -base64 32)
  CONNECTOR_KEY_VERSION="1"
fi

SECRETS_JSON=$( \
  APP_SECRET_VAL="$APP_SECRET_VAL" \
  DATABASE_URL="$DATABASE_URL" \
  WEBHOOK_SECRET_VAL="$WEBHOOK_SECRET_VAL" \
  CONNECTOR_KEY_VAL="$CONNECTOR_KEY_VAL" \
  CONNECTOR_KEY_VERSION="${CONNECTOR_KEY_VERSION:-1}" \
  EXISTING_JSON="$EXISTING_JSON" \
  python3 -c 'import json, os; raw = os.environ["EXISTING_JSON"]; bundle = json.loads(raw) if raw else {}; bundle.update({"APP_SECRET_KEY": os.environ["APP_SECRET_VAL"], "DATABASE_URL": os.environ["DATABASE_URL"], "GITHUB_WEBHOOK_SECRET": os.environ["WEBHOOK_SECRET_VAL"], "CONNECTOR_CREDENTIAL_KEY": os.environ["CONNECTOR_KEY_VAL"], "CONNECTOR_CREDENTIAL_KEY_VERSION": os.environ["CONNECTOR_KEY_VERSION"]}); print(json.dumps(bundle, separators=(",", ":")))' \
)

if [[ -n "$EXISTING_JSON" && "$SECRETS_JSON" == "$EXISTING_JSON" ]]; then
  echo "  - Secret bundle is unchanged. No new version added."
else
  create_or_update_secret "autohub-secrets" "$SECRETS_JSON" "true"
fi


# 5. Create dedicated Service Account & grant secretAccessor role
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "==> Creating dedicated service account: $SA_NAME ($SA_EMAIL)..."
  gcloud iam service-accounts create "$SA_NAME" \
    --project="$PROJECT_ID" \
    --display-name="Auto Hub Service Account"
fi

echo "==> Granting roles/secretmanager.secretAccessor to $SA_EMAIL..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None >/dev/null

echo "==> Secret Manager setup completed successfully!"
echo "    Dedicated Service Account: $SA_EMAIL"
echo "    Secret bundle: autohub-secrets"
if [[ -n "$LOGIN_KEY" ]]; then
  echo "    Save this plaintext API key securely for UI/Scheduler authentication:"
  echo "    $LOGIN_KEY"
else
  echo "    API key unchanged. Use 'just update-api-key' to rotate it everywhere it is used."
fi
