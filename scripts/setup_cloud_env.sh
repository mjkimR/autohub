#!/usr/bin/env bash
# scripts/setup_cloud_env.sh — Cloud environment setup script for autohub
# Usage:
#   ./scripts/setup_cloud_env.sh [codex]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TARGET="${1:-codex}"

case "$TARGET" in
    codex|all)
        ;;
    *)
        echo "Usage: $0 [codex]" >&2
        exit 1
        ;;
esac

echo "==> Configuring cloud environment for target: $TARGET"

# Ensure tool binary paths are prioritized
export UV_TOOL_BIN_DIR="${UV_TOOL_BIN_DIR:-/usr/local/bin}"
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

# 1. uv (Python package and environment manager)
if ! command -v uv >/dev/null 2>&1; then
    echo "==> Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh
else
    echo "==> uv already installed: $(uv --version)"
fi

# 2. just (command runner)
if ! command -v just >/dev/null 2>&1; then
    echo "==> Installing just..."
    if [ -f "$REPO_ROOT/scripts/install-just.sh" ]; then
        bash "$REPO_ROOT/scripts/install-just.sh" /usr/local/bin
    else
        curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
    fi
else
    echo "==> just already installed: $(just --version)"
fi

# 3. apm-cli (for agent skills)
if ! command -v apm >/dev/null 2>&1; then
    echo "==> Installing apm-cli..."
    uv tool install apm-cli==0.30.0
else
    echo "==> apm already installed: $(apm --version 2>/dev/null || true)"
fi

# 4. Node.js (modules/hub-ui requires Node >= 24.18.0)
need_node_install=true
if command -v node >/dev/null 2>&1; then
    NODE_MAJOR="$(node -v | sed -E 's/^v([0-9]+)\..*/\1/')"
    if [ "$NODE_MAJOR" -ge 24 ]; then
        echo "==> Node.js $(node -v) satisfies requirement (>=24)"
        need_node_install=false
    fi
fi

if $need_node_install; then
    echo "==> Installing Node.js 24 via NodeSource..."
    SUDO=""
    if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    fi
    curl -fsSL https://deb.nodesource.com/setup_24.x | $SUDO bash -
    $SUDO apt-get install -y nodejs
fi

# 5. Project dependencies
echo "==> Installing backend Python dependencies..."
uv sync --no-active

echo "==> Installing frontend SvelteKit dependencies..."
npm --prefix modules/hub-ui install

echo "==> Installing agent skills via APM..."
if [ -f "$REPO_ROOT/scripts/install-skills.sh" ]; then
    bash "$REPO_ROOT/scripts/install-skills.sh"
else
    apm install --frozen
fi

# 6. Target-specific configurations
if [ "$TARGET" = "codex" ] || [ "$TARGET" = "all" ]; then
    echo "==> Linking skills for Codex into .codex/skills/..."
    mkdir -p .codex/skills
    if [ -d .agents/skills ]; then
        for skill in .agents/skills/*; do
            [ -e "$skill" ] || continue
            name="$(basename "$skill")"
            ln -sfn "../../.agents/skills/$name" ".codex/skills/$name"
            echo "    linked .codex/skills/$name"
        done
    fi
fi

echo "==> Cloud environment setup complete for $TARGET"

