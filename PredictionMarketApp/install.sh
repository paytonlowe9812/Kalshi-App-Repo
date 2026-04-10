#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
echo "========================================="
echo "  Kalshi Bot Builder - Install"
echo "========================================="
echo ""

# --- Python check ---
info "Checking for Python 3.10+ ..."
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    fail "Python 3 is not installed. Install it from https://www.python.org/downloads/ or via Homebrew: brew install python"
fi

PY_VERSION=$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$($PY -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$($PY -c 'import sys; print(sys.version_info.minor)')

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    fail "Python 3.10+ is required (found $PY_VERSION). Please upgrade."
fi
info "Found Python $PY_VERSION"

# --- Node.js check ---
info "Checking for Node.js ..."
if ! command -v node &>/dev/null; then
    fail "Node.js is not installed. Install it from https://nodejs.org/ or via Homebrew: brew install node"
fi
NODE_VERSION=$(node -v)
info "Found Node.js $NODE_VERSION"

if ! command -v npm &>/dev/null; then
    fail "npm is not installed. It should come with Node.js -- try reinstalling Node."
fi
info "Found npm $(npm -v)"

# --- Create Python virtual environment ---
VENV_DIR="$SCRIPT_DIR/.venv"
if [ -d "$VENV_DIR" ]; then
    info "Virtual environment already exists at .venv"
else
    info "Creating Python virtual environment (.venv) ..."
    $PY -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
info "Activated virtual environment"

# --- Install Python dependencies ---
info "Installing Python dependencies ..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
info "Python dependencies installed"

# --- Install frontend dependencies ---
info "Installing frontend dependencies ..."
cd "$SCRIPT_DIR/frontend"
npm install --no-fund --no-audit
info "Frontend dependencies installed"

# --- Build frontend for production ---
info "Building frontend ..."
npm run build
info "Frontend build complete"

cd "$SCRIPT_DIR"

# --- Create data directory ---
mkdir -p "$SCRIPT_DIR/data"

echo ""
echo "========================================="
echo "  Install complete!"
echo ""
echo "  Run ./launch.sh to start the app."
echo "========================================="
echo ""
