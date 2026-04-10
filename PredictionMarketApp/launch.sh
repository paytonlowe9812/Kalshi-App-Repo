#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC}  $1"; }
fail() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
echo "========================================="
echo "  Kalshi Bot Builder - Launch"
echo "========================================="
echo ""

VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    fail "Virtual environment not found. Run ./install.sh first."
fi

source "$VENV_DIR/bin/activate"

if [ ! -d "$SCRIPT_DIR/frontend/dist" ]; then
    fail "Frontend build not found. Run ./install.sh first."
fi

mkdir -p "$SCRIPT_DIR/data"

info "Starting server on http://127.0.0.1:8080 ..."
echo ""
echo "  Open your browser to:  http://127.0.0.1:8080"
echo ""
echo "  Press Ctrl+C to stop the server."
echo ""

python -m backend.main
