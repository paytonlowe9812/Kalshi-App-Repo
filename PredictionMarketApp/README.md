# Prediction Market App (Kalshi Bot Builder)

Local web app with a FastAPI backend and a React (Vite) frontend for building and running trading bots against Kalshi. The UI talks to the API over `/api`; in development the Vite dev server proxies those requests to the backend.

End-user setup (download, one installer, launch) is in the repository root **[README.md](../README.md)** and **[INSTALL.md](INSTALL.md)**.

## Quick start (this folder)

Prerequisites: **Python 3.10+**, **Node.js 18+** (`npm` on `PATH`).

1. **Install once:** Windows **`install.bat`** or **`.\install.ps1`** — macOS/Linux **`chmod +x install.sh`** then **`./install.sh`**.

2. **Run:** **`python scripts/launch.py`** — or after **`npm install`** in **`frontend/`**, use **`launch.bat`** (Windows) or **`./launch.sh`** (macOS/Linux).

3. Open **http://127.0.0.1:5173**.

The installers create **`.venv/`**, install **`requirements.txt`**, run **`npm install`** in **`frontend/`**, and regenerate **`launch.*`** (those launch files stay gitignored).

## Distribution (maintainers)

For installs without signing in, keep the repo **Public**. Every push to **`main`** runs **`.github/workflows/release-zip.yml`** at the monorepo root: it publishes **`PredictionMarketApp-latest-Windows.zip`**, **`PredictionMarketApp-latest-macOS.tar.gz`**, and **`PredictionMarketApp-latest-Linux.tar.gz`** on a single rolling **Latest** release (tag **`latest`**). Those archives omit **`launch.bat`** and **`launch.sh`** (via **`export-ignore`**); run **`install.*`** or **`python scripts/generate_launchers.py`** after unpacking, then start with **`python scripts/launch.py`** or the generated shortcuts. GitHub Pages for **`docs/index.html`** deploys on **`PredictionMarketApp/**`** changes: **`.github/workflows/pages.yml`**.

## Requirements

- **Python** 3.10+ (3.12 recommended)
- **Node.js** 18+ (LTS) and **npm**
- **Git** only if you clone (not needed for a release download)

## Advanced: two terminals (no launch scripts)

With **`.venv`** activated and dependencies installed (or after **`install.ps1`** / **`install.sh`**):

**Terminal 1 — API**

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Use **`.venv\Scripts\python`** on Windows or **`.venv/bin/python`** on macOS/Linux if you did not activate the venv.

**Terminal 2 — UI**

```bash
cd frontend
npm run dev
```

### Optional: change the API proxy target (frontend)

Set **`VITE_API_PROXY_TARGET`** when starting Vite (see **`frontend/vite.config.js`**).

## Run a production-style build (single server)

Build the frontend into `frontend/dist/`. The FastAPI app serves that folder when it exists.

```bash
cd frontend
npm run build
cd ..
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000**. There is no hot reload on the bundled assets; rebuild after UI changes.

## Data and secrets

- The app stores its SQLite database under **`data/`** (for example `data/app.db`). That directory is listed in `.gitignore` because it can contain **API keys** and personal trading data.
- After cloning, the database is created automatically on first run. Add your Kalshi API credentials in the app under **CONFIG** (or your deployment equivalent).

Do not commit `data/*.db` or share database files publicly.

## Repository hygiene

- **`.cursor/`** and **`.claude/`** are ignored so local editor metadata is not published. If you previously committed them, remove from the index at the appropriate path (repo root vs app folder): `git rm -r --cached .cursor` or `git rm -r --cached .claude`, then commit.
- Keep using a virtual environment and do not commit **`.venv/`** or **`frontend/node_modules/`**.

## License

Add a `LICENSE` file if you distribute this project; none is included by default in this template.
