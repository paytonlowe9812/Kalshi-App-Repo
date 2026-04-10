#!/usr/bin/env bash
# One-step setup: Python venv, pip dependencies, frontend npm install, launch script generation.
# Run from the PredictionMarketApp folder (same folder as backend/ and frontend/).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo ""
echo "Kalshi Bot Builder — install"
echo ""

if command -v python3 >/dev/null 2>&1; then
  PY_BOOT=python3
elif command -v python >/dev/null 2>&1; then
  PY_BOOT=python
else
  echo "ERROR: Python 3.10+ not found. Install from https://www.python.org/downloads/ and retry." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found. Install Node.js LTS from https://nodejs.org/ and retry." >&2
  exit 1
fi

if [ -x "$ROOT/.venv/bin/python" ]; then
  echo "Using existing .venv ..."
else
  echo "Creating virtual environment..."
  "$PY_BOOT" -m venv "$ROOT/.venv"
fi

VENV_PY="$ROOT/.venv/bin/python"
echo "Installing Python packages..."
"$VENV_PY" -m pip install --upgrade pip -q
"$VENV_PY" -m pip install -r "$ROOT/requirements.txt"

echo "Installing frontend (npm)..."
( cd "$ROOT/frontend" && npm install )

echo ""
echo "Install finished."
echo "Start the app:  ./launch.sh"
echo ""
