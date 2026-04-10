## Installation and setup

### Requirements

- **Python** 3.10 or newer (3.12 recommended)
- **Node.js** 18 or newer (LTS) and **npm**
- **Git** (only if you clone; not needed for a ZIP download)

Optional: a **virtual environment** for Python.

### Shareable links (replace `YOUR-GITHUB-USERNAME` and `YOUR-REPO-NAME`)

| Purpose | URL |
|--------|-----|
| **This install guide** (markdown at repo root) | `https://github.com/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME/blob/main/README.md` |
| Install page (**GitHub Pages**, styled) | `https://YOUR-GITHUB-USERNAME.github.io/YOUR-REPO-NAME/` |
| Condensed install (markdown under app folder) | `https://github.com/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME/blob/main/PredictionMarketApp/INSTALL.md` |
| Direct ZIP of latest `main` | `https://github.com/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME/archive/refs/heads/main.zip` |
| **Latest release — Windows** (`.zip`) | `https://github.com/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME/releases/latest/download/PredictionMarketApp-Windows.zip` |
| **Latest release — macOS** (`.tar.gz`) | `https://github.com/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME/releases/latest/download/PredictionMarketApp-macOS.tar.gz` |
| **Latest release — Linux** (`.tar.gz`) | `https://github.com/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME/releases/latest/download/PredictionMarketApp-Linux.tar.gz` |

For anonymous public downloads, the repository must be **Public**. Enable **Settings → Pages → Source: GitHub Actions** for the Pages URL; workflow: **`.github/workflows/pages.yml`**.

### Get the code

**Download ZIP (no Git):** GitHub **Code → Download ZIP**, extract, then open **`PredictionMarketApp/`** inside the archive (the folder that contains `backend/`, `frontend/`, and `requirements.txt`). That folder is your working directory for all commands below.

**Clone:**

```bash
git clone <your-repo-url>
cd PredictionMarketApp
```

If you cloned the full monorepo, `cd` into **`PredictionMarketApp/`** first.

**Release archives:** Each platform archive contains a **`PredictionMarketApp/`** tree. Open that folder as the app root. A one-line **`PredictionMarketApp/.release-platform`** file may be present so releases upload reliably; you can delete it after extracting.

### Install dependencies

Run these from **`PredictionMarketApp/`** (app root).

**Windows (PowerShell or Command Prompt)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

If `python3` is not available, use `python` where your system provides Python 3.10+.

**`npm install`** in **`frontend/`** runs a postinstall step that creates **`launch.ps1`**, **`launch.bat`**, and **`launch.sh`** in the app root (gitignored). If Python was not found, fix `PATH` and run **`npm install`** again in **`frontend/`**, or run **`python scripts/generate_launchers.py`** from the app root.

### Run in development (two terminals)

From **`PredictionMarketApp/`**, with the virtual environment activated.

**Terminal 1 — API (port 8000)**

Windows:

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

macOS / Linux:

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Use `python3` if that is how you invoke Python.

**Terminal 2 — UI (port 5173)**

```bash
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173**. The Vite dev server proxies `/api` to **http://127.0.0.1:8000** by default.

**Optional — change API proxy:** set `VITE_API_PROXY_TARGET` when starting Vite (see `frontend/vite.config.js`).

```bash
# macOS / Linux
VITE_API_PROXY_TARGET=http://127.0.0.1:9000 npm run dev
```

```powershell
# Windows PowerShell
$env:VITE_API_PROXY_TARGET="http://127.0.0.1:9000"; npm run dev
```

### Windows: one-step launcher

After **`npm install`** in **`frontend/`** (or **`python scripts/generate_launchers.py`**):

```powershell
.\launch.ps1
```

Or double-click **`launch.bat`**. On **macOS / Linux**, use **`./launch.sh`** after generating launchers.

### Production-style build (single server)

From **`PredictionMarketApp/`**:

```bash
cd frontend
npm run build
cd ..
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Rebuild the frontend after UI changes.

### Data and secrets

The app stores SQLite under **`PredictionMarketApp/data/`**. That directory is gitignored. Do not commit database files or share them publicly. Add Kalshi API credentials in the app under **CONFIG** after first run.

### Repository hygiene

- **`.claude/`** and **`.cursor/`** are ignored at the repo and app level so local editor metadata is not published. If they were committed earlier, remove them with `git rm -r --cached .claude` at the repo root (or the tracked path), then commit and push.
- Do not commit **`.venv/`** or **`frontend/node_modules/`**.

### More detail

Feature overview, private-repo download notes, and extra context: **[PredictionMarketApp/README.md](PredictionMarketApp/README.md)**. Shorter duplicate with shareable links only: **[PredictionMarketApp/INSTALL.md](PredictionMarketApp/INSTALL.md)**.
