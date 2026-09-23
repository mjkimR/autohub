#!/usr/bin/env bash
# scripts/setup_cloud_env.sh — Cloud environment setup and maintenance script for autohub
# Usage:
#   ./scripts/setup_cloud_env.sh [codex|claude|all]        # Full setup (tools + init)
#   ./scripts/setup_cloud_env.sh --init [codex|claude|all] # Fast maintenance sync (dependencies + skills)
#   ./scripts/setup_cloud_env.sh init                      # Fast maintenance sync alias
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODE="setup"
TARGET="codex"

for arg in "$@"; do
    case "$arg" in
        --init|init)
            MODE="init"
            ;;
        codex|claude|all)
            TARGET="$arg"
            ;;
        -h|--help)
            echo "Usage: $0 [--init] [codex|claude|all]"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            echo "Usage: $0 [--init] [codex|claude|all]" >&2
            exit 1
            ;;
    esac
done

# Ensure tool binary paths are prioritized (support both root and non-root users)
if [ -w /usr/local/bin ]; then
    export UV_TOOL_BIN_DIR="${UV_TOOL_BIN_DIR:-/usr/local/bin}"
else
    export UV_TOOL_BIN_DIR="${UV_TOOL_BIN_DIR:-$HOME/.local/bin}"
fi
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

if [ -w /etc/profile.d ]; then
    echo 'export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"' > /etc/profile.d/cloud_env.sh 2>/dev/null || true
fi

do_init() {
    echo "==> [init] Syncing Python dependencies..."
    uv sync --no-active

    echo "==> [init] Installing frontend SvelteKit dependencies..."
    npm --prefix modules/hub-ui install

    echo "==> [init] Syncing agent skills via APM..."
    if [ -f "$REPO_ROOT/scripts/install-skills.sh" ]; then
        bash "$REPO_ROOT/scripts/install-skills.sh"
    elif command -v apm >/dev/null 2>&1; then
        apm install --frozen
    fi

    # Link skills for Codex if target is codex or all
    if [ "$TARGET" = "codex" ] || [ "$TARGET" = "all" ]; then
        echo "==> [init] Linking skills for Codex into .codex/skills/..."
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
}

do_setup() {
    echo "==> [setup] Configuring cloud environment for target: $TARGET"

    # 1. uv (Python package and environment manager)
    if ! command -v uv >/dev/null 2>&1; then
        echo "==> [setup] Installing uv..."
        INSTALL_DIR="/usr/local/bin"
        [ ! -w /usr/local/bin ] && INSTALL_DIR="$HOME/.local/bin"
        curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$INSTALL_DIR" sh
    else
        echo "==> [setup] uv already installed: $(uv --version)"
    fi

    # 2. just (command runner)
    if ! command -v just >/dev/null 2>&1; then
        echo "==> [setup] Installing just..."
        INSTALL_DIR="/usr/local/bin"
        [ ! -w /usr/local/bin ] && INSTALL_DIR="$HOME/.local/bin"
        mkdir -p "$INSTALL_DIR"
        curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to "$INSTALL_DIR" --force
    else
        echo "==> [setup] just already installed: $(just --version)"
    fi

    # Ensure both /usr/local/bin and ~/.local/bin have just available
    if [ -x /usr/local/bin/just ] && [ -d "$HOME/.local/bin" ] && [ ! -e "$HOME/.local/bin/just" ]; then
        ln -sfn /usr/local/bin/just "$HOME/.local/bin/just" 2>/dev/null || true
    elif [ -x "$HOME/.local/bin/just" ] && [ -w /usr/local/bin ] && [ ! -e /usr/local/bin/just ]; then
        ln -sfn "$HOME/.local/bin/just" /usr/local/bin/just 2>/dev/null || true
    fi

    # 3. apm-cli (for agent skills)
    if ! command -v apm >/dev/null 2>&1; then
        echo "==> [setup] Installing apm-cli..."
        uv tool install apm-cli==0.30.0
    else
        echo "==> [setup] apm already installed: $(apm --version 2>/dev/null || true)"
    fi

    # 4. Node.js (modules/hub-ui requires Node >= 24.18.0)
    need_node_install=true
    if command -v node >/dev/null 2>&1; then
        NODE_MAJOR="$(node -v | sed -E 's/^v([0-9]+)\..*/\1/')"
        if [ "$NODE_MAJOR" -ge 24 ]; then
            echo "==> [setup] Node.js $(node -v) satisfies requirement (>=24)"
            need_node_install=false
        fi
    fi

    if $need_node_install; then
        echo "==> [setup] Installing Node.js 24 via NodeSource..."
        SUDO=""
        if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
            SUDO="sudo"
        fi
        curl -fsSL https://deb.nodesource.com/setup_24.x | $SUDO bash -
        $SUDO apt-get install -y nodejs
    fi

    # 5. Run init
    do_init

    echo "==> [setup] Cloud environment setup complete for $TARGET"
}

if [ "$MODE" = "init" ]; then
    do_init
    echo "==> Cloud environment initialized successfully for $TARGET"
else
    do_setup
fi
