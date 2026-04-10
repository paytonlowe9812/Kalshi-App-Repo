#!/usr/bin/env python3
"""
Start Kalshi Bot Builder: FastAPI on :8000 and Vite dev server on :5173.

Run from the app root (folder that contains backend/ and frontend/):

    python scripts/launch.py

After install, you can also use the generated shortcuts (local only, not in git):
  Windows: double-click launch.bat
  macOS/Linux: ./launch.sh
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


def _resolve_python() -> str:
    if sys.platform == "win32":
        venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = ROOT / ".venv" / "bin" / "python"
    if venv_py.is_file():
        return str(venv_py)
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return found
    print("ERROR: Python not found. Run install.ps1 / install.sh once, then retry.", file=sys.stderr)
    sys.exit(1)


def _free_ports(*ports: int) -> None:
    for port in ports:
        if sys.platform == "win32":
            ps = (
                f"$c = Get-NetTCPConnection -State Listen -LocalPort {port} "
                "-ErrorAction SilentlyContinue; "
                "$c | ForEach-Object { "
                "Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                cwd=str(ROOT),
            )
        else:
            subprocess.run(
                f"lsof -ti :{port} | xargs kill -9 2>/dev/null || true",
                shell=True,
                cwd=str(ROOT),
            )


def _ensure_frontend_deps() -> None:
    if not shutil.which("npm"):
        print("ERROR: npm not found. Install Node.js LTS.", file=sys.stderr)
        sys.exit(1)
    if not (FRONTEND / "node_modules").is_dir():
        print("[INFO] Running npm install in frontend...")
        subprocess.run(["npm", "install"], cwd=str(FRONTEND), check=True)


def _ensure_backend_deps(py: str) -> None:
    r = subprocess.run(
        [py, "-c", "import fastapi, uvicorn"],
        cwd=str(ROOT),
        capture_output=True,
    )
    if r.returncode != 0:
        print("[INFO] Installing Python dependencies...")
        subprocess.run(
            [py, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
            cwd=str(ROOT),
            check=True,
        )


def main() -> int:
    if not (ROOT / "backend").is_dir() or not FRONTEND.is_dir():
        print("ERROR: Run from app root (folder with backend/ and frontend/).", file=sys.stderr)
        return 1

    py = _resolve_python()
    _ensure_frontend_deps()
    _ensure_backend_deps(py)

    _free_ports(8000, 5173)
    time.sleep(0.5)

    print("")
    print("========================================")
    print("  Kalshi Bot Builder")
    print("========================================")
    print("  Backend  -> http://127.0.0.1:8000")
    print("  Frontend -> http://127.0.0.1:5173")
    print("")
    print("  Press Ctrl+C here to stop both.")
    print("========================================")
    print("")

    backend = subprocess.Popen(
        [
            py,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(ROOT),
    )

    time.sleep(1.5)
    if backend.poll() is not None:
        print(
            f"ERROR: Backend exited immediately (exit code {backend.returncode}). "
            "Fix the error above, then try again.",
            file=sys.stderr,
        )
        return 1

    def _wait_port(host: str, port: int, timeout: float = 90.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with socket.create_connection((host, port), timeout=1.0):
                    return True
            except OSError:
                time.sleep(0.25)
        return False

    def _open_browser_when_ready() -> None:
        if _wait_port("127.0.0.1", 5173):
            webbrowser.open("http://127.0.0.1:5173/")
        else:
            print(
                "ERROR: Dev server did not open on http://127.0.0.1:5173 in time. "
                "Scroll up for npm/Vite errors.",
                file=sys.stderr,
            )

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    try:
        npm = shutil.which("npm")
        if not npm:
            print("ERROR: npm not found.", file=sys.stderr)
            return 1
        subprocess.run([npm, "run", "dev"], cwd=str(FRONTEND), check=False)
    except KeyboardInterrupt:
        pass
    finally:
        backend.terminate()
        try:
            backend.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend.kill()
            backend.wait(timeout=2)

    print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
