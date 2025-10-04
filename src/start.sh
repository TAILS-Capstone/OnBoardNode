#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BASE_DIR
ENV_SETUP_DIR="$BASE_DIR/environment_setup"
if [[ ! -d "$ENV_SETUP_DIR" ]]; then
  echo "[start][error] environment_setup directory not found at $ENV_SETUP_DIR" >&2
  exit 1
fi
# Predefine ZSH_VERSION so setup_env.sh can reference it without set -u errors
: "${ZSH_VERSION:=}"
# Predefine VIRTUAL_ENV similarly to avoid unbound variable error
: "${VIRTUAL_ENV:=}"

echo "[start] Sourcing setup_env.sh (will create/activate venv if missing)..."
# shellcheck source=/dev/null
source "$ENV_SETUP_DIR/setup_env.sh"
# Ensure we are back at script dir (setup_env.sh may cd elsewhere)
cd "$BASE_DIR"

echo "[start] Running install.sh inside virtual environment..."
bash "$ENV_SETUP_DIR/install.sh"

MAIN_SCRIPT="$BASE_DIR/main.py"
if [[ ! -f "$MAIN_SCRIPT" ]]; then
  echo "[start][error] main.py not found at $MAIN_SCRIPT" >&2
  exit 1
fi

# Logging env: unbuffered Python + configurable level (default INFO)
export PYTHONUNBUFFERED=1
: "${APP_LOG_LEVEL:=INFO}"
export APP_LOG_LEVEL

echo "[start] Launching main..."
exec python3 "$MAIN_SCRIPT" -i rpi --headless
