#!/bin/bash
set -e

echo "=== Kalshi Bot Builder Installer ==="

cd "$(dirname "$0")/../.."

echo "[1/4] Installing Python dependencies..."
pip install -r requirements.txt

echo "[2/4] Installing frontend dependencies..."
cd frontend
npm install
npm run build
cd ..

echo "[3/4] Creating data directory..."
mkdir -p data

echo "[4/4] Done! Starting server..."
echo "Open http://localhost:8080 in your browser"
python -m backend.main
