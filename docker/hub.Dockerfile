# ---- Frontend Builder Stage ----
FROM node:22-slim AS frontend-builder
WORKDIR /app/modules/hub-ui

COPY modules/hub-ui/package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

COPY modules/hub-ui ./
RUN npm run build

# ---- Pinned specrig and offline restoration cache ----
FROM python:3.13-slim AS specrig-builder
RUN apt-get update && apt-get install -y --no-install-recommends gh git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /provision
COPY config/specrig-release.json config/specrig-release.json
COPY scripts/install-specrig.py scripts/install-specrig.py
# Private release access is build-only; no token is copied to the runtime.
RUN --mount=type=secret,id=specrig_token \
    if [ -f /run/secrets/specrig_token ]; then export GH_TOKEN="$(cat /run/secrets/specrig_token)"; fi; \
    python scripts/install-specrig.py /opt/specrig

# ---- Backend Builder Stage ----
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS backend-builder
ENV TZ=UTC
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# uv workspace: root pyproject.toml + uv.lock, then member pyproject.toml
COPY pyproject.toml uv.lock ./
COPY modules/hub/pyproject.toml ./modules/hub/pyproject.toml
COPY packages/sdk ./packages/sdk

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable --no-dev --package scheduler-mgr

# ---- Final Stage ----
FROM python:3.13-slim AS runtime
ENV TZ=UTC
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
ENV AUTOHUB_SPECRIG_HOME=/opt/specrig
ENV PATH="/opt/specrig/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user setup
RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -m appuser

WORKDIR /app/modules/hub
COPY --from=specrig-builder --chown=appuser:appuser /opt/specrig /opt/specrig
COPY --from=backend-builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=frontend-builder --chown=appuser:appuser /app/modules/hub-ui/build ./ui_dist
COPY --chown=appuser:appuser modules/hub/app ./app
COPY --chown=appuser:appuser modules/hub/alembic.ini ./alembic.ini
COPY --chown=appuser:appuser modules/hub/migrations ./migrations
COPY --chown=appuser:appuser templates/github-actions /app/templates/github-actions
COPY --chmod=755 docker/run_hub.sh ./run_hub.sh

USER appuser

ENV WORKERS=3
ENV TIMEOUT=1200

ENTRYPOINT ["./run_hub.sh"]
