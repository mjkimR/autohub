# Cloud Run Deployment Guide

This guide covers the end-to-end process of deploying Auto Hub to Google Cloud Run.  
The FastAPI backend (`modules/hub`) and Svelte 5 frontend (`modules/hub-ui`) are built and deployed together in a single consolidated container.

---

## ⚡ Quick Start (Using Helper Scripts)

Automated scripts are available under `docker/helper/`, allowing you to configure secrets and deploy with a single command:

- **GCS Staging Bucket**: The temporary source bucket for Cloud Build is created in the selected deployment region and automatically cleaned up after the build.
- **Cloud Run & Artifact Registry**: Default to **`us-west1` (Oregon)** for North America network-cost optimization; pass `REGION` or `--region` when another region is required.

```bash
# [Case A: Using Aiven or External PostgreSQL (Recommended - 100% Free)]
# 1) Set up secrets
just setup-secrets -e "you@example.com" -b "postgresql+psycopg://avnadmin:<PASSWORD>@<HOST>:<PORT>/defaultdb?sslmode=require"

# 2) Deploy to Cloud Run (runs directly without Cloud SQL flag)
just deploy-cloud-run

# [Case B: Using Google Cloud SQL]
# 1) Set up secrets
just setup-secrets -e "you@example.com" -c "PROJECT:REGION:INSTANCE"

# 2) Deploy to Cloud Run
just deploy-cloud-run -c "PROJECT:REGION:INSTANCE"
```

`just setup-secrets` is safe to re-run, for example to change the database URL: it keeps every value the `autohub-secrets` bundle already holds unless an option replaces it, and never regenerates the connector credential key (which would make stored connector credentials undecryptable) or the webhook secret. It refuses to run when the bundle exists but cannot be read. Change the operator's password with `just update-password`, which updates the bundle and restarts Cloud Run; the hub applies the bundle's password to the account at startup. Cloud Scheduler is not involved: it uses its own `SCHEDULER_KEY`.

_(To run each step manually, see steps 1 through 6 below.)_

---

## 1. Prerequisites (GCP Environment Setup)

### 1.1 Set GCP Project and Variables

```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-west1" # Oregon (North America)
export SERVICE_NAME="autohub"
export REPO_NAME="autohub"
export DB_INSTANCE_NAME="autohub-db"

gcloud config set project "$PROJECT_ID"
```

### 1.2 Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

---

## 2. Database (Cloud SQL for PostgreSQL)

### 2.1 Create Cloud SQL Instance (If creating new)

> [!NOTE]
> If you already have an active PostgreSQL instance, skip this step and proceed to 2.2 to create the database and user.

```bash
gcloud sql instances create "$DB_INSTANCE_NAME" \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region="$REGION" \
  --root-password="<STRONG_ROOT_PASSWORD>"
```

### 2.2 Create Database and User

```bash
# Create database
gcloud sql databases create auto_hub --instance="$DB_INSTANCE_NAME"

# Create application user
gcloud sql users create hub_user \
  --instance="$DB_INSTANCE_NAME" \
  --password="<STRONG_USER_PASSWORD>"
```

---

## 3. Secret Manager Configuration

All Auto Hub secrets are stored as one JSON payload and injected through `APP_SECRETS_JSON`.
The setup helper generates the bundle. Pass `--email` the first time (the address you sign in with) and optionally `--app-secret` (your password); a password is generated and printed once when you omit it:

```bash
just setup-secrets -- --project "$PROJECT_ID" --connection-name "$DB_CONNECTION_NAME" --email "you@example.com"
```

The bundle contains the operator's account (`FIRST_USER_EMAIL`, `FIRST_USER_PASSWORD`,
`FIRST_USER_SYNC_PASSWORD`), the token signing key (`SECRET_KEY`), the scheduler's key
(`SCHEDULER_KEY`), how long an unused session lasts (`REFRESH_TOKEN_EXPIRE_DAYS`, 7), `DATABASE_URL`, `GITHUB_WEBHOOK_SECRET`, `CONNECTOR_CREDENTIAL_KEY`, and
`CONNECTOR_CREDENTIAL_KEY_VERSION`. A bundle written before accounts existed is upgraded in place by
re-running the helper: `APP_SECRET_KEY` is removed and the new values are added. The app-common
environment loader expands these into normal environment variables at startup.

### 3.1 Database Connection URL (`DATABASE_URL`)

Cloud Run connects via Cloud SQL Unix Domain Socket (`/cloudsql/PROJECT:REGION:INSTANCE`):

```bash
# Retrieve Cloud SQL Connection Name
export DB_CONNECTION_NAME=$(gcloud sql instances describe "$DB_INSTANCE_NAME" --format="value(connectionName)")

# Format: postgresql+psycopg://<USER>:<PASSWORD>@/<DB_NAME>?host=/cloudsql/<CONNECTION_NAME>
export DATABASE_URL="postgresql+psycopg://hub_user:<STRONG_USER_PASSWORD>@/auto_hub?host=/cloudsql/${DB_CONNECTION_NAME}"
# Pass DATABASE_URL to the setup helper, or use --database-url directly.
```

---

## 4. Service Account (IAM) Permissions

Grant Cloud SQL and Secret Manager access to the default Cloud Run Compute Service Account (or a custom dedicated service account).

```bash
export PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
export RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Secret Manager Secret Accessor
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUN_SA}" \
  --role="roles/secretmanager.secretAccessor"

# Cloud SQL Client
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUN_SA}" \
  --role="roles/cloudsql.client"
```

---

## 5. Container Build & Cloud Run Deployment

Even without a local Docker daemon, you can build directly in the cloud using **Google Cloud Build**.

### 5.1 Create Artifact Registry Repository

```bash
gcloud artifacts repositories create "$REPO_NAME" \
  --repository-format=docker \
  --location="$REGION" \
  --description="Auto Hub docker repository"
```

### 5.2 Build & Push with Cloud Build

Run this from the project root directory:

```bash
export IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:latest"

gcloud builds submit \
  --config=<(cat <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  env: ['DOCKER_BUILDKIT=1']
  args: ['build', '-f', 'docker/hub.Dockerfile', '-t', '${IMAGE_URI}', '.']
images:
- '${IMAGE_URI}'
timeout: '1200s'
EOF
) .
```

### 5.3 Deploy Cloud Run Service

```bash
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_URI" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8389 \
  --timeout=1200 \
  --memory=1Gi \
  --cpu=1 \
  --add-cloudsql-instances="$DB_CONNECTION_NAME" \
  --set-secrets="APP_SECRETS_JSON=autohub-secrets:latest"
```

Record the deployed Service URL output (e.g. `https://autohub-xxxx-du.a.run.app`):

```bash
export SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)")
echo "Auto Hub Service URL: $SERVICE_URL"
```

---

## 6. Register Cloud Scheduler (Periodic Trigger)

Set up Cloud Scheduler to invoke Auto Hub's observation and retry dispatcher ticks every minute.

```bash
gcloud scheduler jobs create http autohub-dispatcher-tick \
  --location="$REGION" \
  --schedule="* * * * *" \
  --uri="${SERVICE_URL}/api/v1/dispatchers/trigger" \
  --http-method=POST \
  --headers="X-Scheduler-Key=$(gcloud secrets versions access latest --secret=autohub-secrets | python3 -c 'import json,sys; print(json.load(sys.stdin)["SCHEDULER_KEY"])')" \
  --time-zone="UTC" \
  --attempt-deadline=300s
```

---

## 7. Post-Deployment Verification & Integration

1. **Verify Web Browser Access**
   - Navigate to `${SERVICE_URL}/` and verify that the Hub UI dashboard loads properly.
   - Sign in with the email and password given to `just setup-secrets`.
2. **Verify Swagger Docs**
   - Access `${SERVICE_URL}/docs` and verify the OpenAPI interactive documentation responds.
3. **Register GitHub Repository Webhook**

   **Method A: Automatic Registration via CLI (Recommended)**:
   Automatically retrieves Google Cloud Secrets and the Cloud Run URL to register or update the webhook on the target repository in seconds:

   ```bash
   just register-webhook <owner/repo>
   # Example: just register-webhook mjkimR/my-repo
   ```

   **Method B: Manual Registration via GitHub Web Console**:
   - Go to `Settings → Webhooks → Add webhook` on your target GitHub repository.
   - **Payload URL**: `${SERVICE_URL}/api/github/webhooks`
   - **Content type**: `application/json`
   - **Secret**: `GITHUB_WEBHOOK_SECRET` value from the `autohub-secrets` bundle
   - **Events**: Select `Let me select individual events` and check:
     - `Pull requests`
     - `Issue comments`
     - `Workflow runs`
   - After creating, check `Recent Deliveries` to confirm Ping delivery returns 200/202 OK.

4. **End-to-End Testing**
   - Enroll a project and pull request in the UI (or include `@auto-run`, optionally `@auto-run:<catalog key or kind>`, in the PR description / comments) to verify automated dispatch and CI monitoring progression.
