# Prediction Market App (Kalshi Bot Builder)

Local web app with a FastAPI backend and a React (Vite) frontend for building and running trading bots against Kalshi. The UI talks to the API over `/api`; in development the Vite dev server proxies those requests to the backend.

## Public install (share one link)

To let **anyone** download and install **without a GitHub account**, the repository must be **Public** (GitHub: **Settings → General → Danger zone → Change visibility**).

**Share any of these** (replace `YOUR-GITHUB-USERNAME` and, if needed, `PredictionMarketApp`):

| Purpose | URL |
|--------|-----|
| Install page (**GitHub Pages**, styled) | `https://YOUR-GITHUB-USERNAME.github.io/PredictionMarketApp/` |
| Install guide (markdown on GitHub) | `https://github.com/YOUR-GITHUB-USERNAME/PredictionMarketApp/blob/main/INSTALL.md` |
| Direct ZIP of latest `main` | `https://github.com/YOUR-GITHUB-USERNAME/PredictionMarketApp/archive/refs/heads/main.zip` |
| Direct ZIP of **latest release** | `https://github.com/YOUR-GITHUB-USERNAME/PredictionMarketApp/releases/latest/download/PredictionMarketApp.zip` |

The **release** link works after you push at least one version tag (for example `v1.0.0`); see [.github/workflows/release-zip.yml](.github/workflows/release-zip.yml).

**Pages:** enable **Settings → Pages → Source: GitHub Actions**, then push `docs/` (see [.github/workflows/pages.yml](.github/workflows/pages.yml)).

The same instructions live in **[INSTALL.md](INSTALL.md)** and **[docs/index.html](docs/index.html)**.

## Requirements

- **Python** 3.10 or newer (3.12 recommended)
- **Node.js** 18 or newer (LTS) and **npm**
- **Git** (only if you clone the repository; not needed for a ZIP download)

Optional but recommended: a **virtual environment** for Python so dependencies do not clash with other projects.

## Download as ZIP (no Git)

GitHub hosts the project in two convenient ways:

### Option A: Latest code from the default branch

1. Open your repository on GitHub.
2. Click the green **Code** button.
3. Choose **Download ZIP**.
4. Extract the archive. The folder name is usually `PredictionMarketApp-main` (or `PredictionMarketApp-<branch>`), not necessarily `PredictionMarketApp`. Open the folder that contains `backend/`, `frontend/`, and `requirements.txt`.
5. Continue from **[Install dependencies](#install-dependencies)** below (use that folder as the project root in your terminal).

This ZIP only includes files tracked in Git (no `node_modules`, `.venv`, or database files).

### Option B: Versioned ZIP from Releases

If this repository uses [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases), each tagged version (for example `v1.0.0`) gets **`PredictionMarketApp-v1.0.0.zip`** plus a stable **`PredictionMarketApp.zip`** (same contents) attached to the release.

Maintainers create a release by pushing a tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow in `.github/workflows/release-zip.yml` builds those ZIPs automatically. For a **public** repo, anyone can use **`/releases/latest/download/PredictionMarketApp.zip`** without logging in. Others can open the **Releases** page or follow **[INSTALL.md](INSTALL.md)**.

### Option C: ZIP from GitHub Actions (every push to `main`)

Each successful push to the **`main`** branch runs `.github/workflows/main-branch-zip.yml` and uploads **`PredictionMarketApp-main.zip`** as a workflow artifact (not a Release).

1. Open the repository on GitHub and go to the **Actions** tab.
2. Select **Main branch ZIP artifact** in the workflow list.
3. Open the latest successful run.
4. Scroll to **Artifacts** and download **PredictionMarketApp-main**.

Artifacts are stored for **90 days** (`retention-days` in the workflow), after which GitHub deletes them. This is useful for testers who want the latest `main` without using Git. Downloading artifacts usually requires a **GitHub login**; for anonymous public downloads use the **[INSTALL.md](INSTALL.md)** links (branch archive or release ZIP) instead.

### Private repositories

If the repository is **private**, anyone downloading a ZIP must have **read access** to the repo (collaborator, team member, or organization member with appropriate permissions).

- **Code → Download ZIP** and **Releases** assets only work in the browser when you are **signed in** to a GitHub account that is allowed to view the repository.
- Do **not** share personal access tokens (PATs) or passwords in chat or commit them to the project.

**Download with the GitHub CLI** (after `gh auth login` with a user that can read the repo):

```bash
gh auth login
gh repo clone OWNER/REPO PredictionMarketApp
```

Replace `OWNER` and `REPO` with your GitHub owner and repository name.

**Download the default branch as a ZIP using your `gh` login** (`curl -L` follows GitHub’s redirect to `codeload.github.com`; change `main` if your default branch has another name):

```bash
gh auth login
curl -fL -H "Authorization: Bearer $(gh auth token)" \
  -o PredictionMarketApp-main.zip \
  "https://api.github.com/repos/OWNER/REPO/zipball/main"
```

For a **release** asset, use **Releases** in the browser, or `gh release download TAG` with a repo that has releases, or the [GitHub REST API for release assets](https://docs.github.com/en/rest/releases/assets) with a token that has `repo` scope (classic) or **Contents: Read** (fine-grained, for that repository).

**Download with `curl`** (classic PAT with `repo` scope, or a fine-grained token with read access to repository contents):

```bash
curl -sL \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -o PredictionMarketApp-main.zip \
  "https://api.github.com/repos/OWNER/REPO/zipball/main"
```

Use a short-lived token, revoke it when no longer needed, and never paste tokens into issues or public documents.

## Clone the repository

If you use Git:

```bash
git clone <your-repo-url>
cd PredictionMarketApp
```

## Install dependencies

### Python (all platforms)

From the repository root (the folder that contains `backend/` and `requirements.txt`):

**Windows (PowerShell or Command Prompt)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `python3` is not available, use `python` where your system provides Python 3.10+.

### Frontend (all platforms)

```bash
cd frontend
npm install
cd ..
```

## Run in development (two terminals)

You must start the **backend** and **frontend** separately. Run all commands from the repository root unless noted.

**Terminal 1 – API (port 8000)**

Windows:

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

macOS / Linux:

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Use `python3` if that is how you invoke Python on your machine.

**Terminal 2 – UI (port 5173)**

```bash
cd frontend
npm run dev
```

Open the app in a browser at **http://127.0.0.1:5173** (or the URL Vite prints). The dev server proxies `/api` to **http://127.0.0.1:8000** by default.

### Optional: change the API proxy target (frontend)

If the API listens on another host or port, set `VITE_API_PROXY_TARGET` when starting Vite (see `frontend/vite.config.js`). Example:

```bash
# macOS / Linux
VITE_API_PROXY_TARGET=http://127.0.0.1:9000 npm run dev
```

```powershell
# Windows PowerShell
$env:VITE_API_PROXY_TARGET="http://127.0.0.1:9000"; npm run dev
```

## Windows: one-step launcher

If you use PowerShell, you can start the backend and frontend in separate windows and open the browser with:

```powershell
.\launch.ps1
```

The script checks for Python and npm, installs missing `frontend/node_modules` or Python packages when needed, and frees ports 8000 and 5173 before starting (see `launch.ps1` for details).

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

- **`.cursor/`** and similar editor-only paths are ignored so local Cursor rules and agent metadata are not published. If you previously committed `.cursor/`, remove it from the index once: `git rm -r --cached .cursor` then commit.
- Keep using a virtual environment and do not commit **`.venv/`** or **`frontend/node_modules/`**.

## License

Add a `LICENSE` file if you distribute this project; none is included by default in this template.
