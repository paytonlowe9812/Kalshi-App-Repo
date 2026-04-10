# Install from a public download

These steps work for **anyone** with a normal browser. No GitHub account is needed as long as the repository is **Public**.

**Maintainers:** Replace `YOUR-GITHUB-USERNAME` with your GitHub user or organization (for example `octocat`). Replace `YOUR-REPO-NAME` with this **GitHub repository name** (for `github.com/you/Kalshi-App-Repo`, use `Kalshi-App-Repo` — not the `PredictionMarketApp` folder name). If your default branch is not `main`, change `main` in the download URLs.

---

## Shareable links

Send people **one** of these:

| What | Link |
|------|------|
| **This install guide** (GitHub Pages site) | `https://YOUR-GITHUB-USERNAME.github.io/YOUR-REPO-NAME/` |
| **This install guide** (markdown in repo) | `https://github.com/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME/blob/main/PredictionMarketApp/INSTALL.md` |
| **Download latest source** (`main` branch, always current) | `https://github.com/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME/archive/refs/heads/main.zip` |
| **Download latest release** (app subtree; after first version tag) | `https://github.com/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME/releases/latest/download/PredictionMarketApp.zip` |

The **source** and **release** ZIPs contain the same tracked files as a `git clone` (no `node_modules`, no `.venv`, no database).

### GitHub Pages (maintainers)

To serve the styled install page at `https://YOUR-GITHUB-USERNAME.github.io/YOUR-REPO-NAME/`:

1. **Settings** → **Pages** → **Build and deployment** → set **Source** to **GitHub Actions**.
2. Ensure **`.github/workflows/pages.yml` exists at the repository root** (for this monorepo it lives next to `PredictionMarketApp/`, not inside it). Push to `main`, or open **Actions** → **Deploy Pages** → **Run workflow**.

---

## Make the repository public (maintainers)

1. On GitHub: **Settings** → **General** → **Danger Zone** → **Change repository visibility** → **Public**.
2. Push a version tag once so the **latest release** link works, for example:

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

   The workflow attaches `PredictionMarketApp.zip` to that release. After that, `releases/latest/download/PredictionMarketApp.zip` always points at the newest release.

---

## After downloading

1. Unzip the file.
2. Open the folder that contains **`backend`**, **`frontend`**, and **`requirements.txt`** (the **project root** for install commands).
   - If you downloaded the **full repository** ZIP, you may see a top folder like `Kalshi-App-Repo-main`, then open **`PredictionMarketApp`** inside it.
   - If you downloaded the **release** ZIP (`PredictionMarketApp.zip`), paths inside the archive usually start with **`PredictionMarketApp/`** — open that folder (or use it as the root if your unzipper flattens one level).
   - GitHub sometimes names archives `…-main`; that is fine.

### What you need installed

- **Python** 3.10+ ([python.org](https://www.python.org/downloads/))
- **Node.js** 18+ LTS and **npm** ([nodejs.org](https://nodejs.org/))

### Install dependencies

Open a terminal **in the project root** (the folder with `requirements.txt`).

**Windows (PowerShell)**

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

The **`npm install`** step runs on **Windows, macOS, and Linux** and automatically creates **`launch.ps1`**, **`launch.bat`**, and **`launch.sh`** in the project root (they are not in Git). If you see a warning that Python was not found, fix `PATH` and run **`npm install`** again inside **`frontend/`**, or run **`python scripts/generate_launchers.py`** from the project root.

### Run the app (two terminals)

Keep the virtual environment activated. From the **project root**:

**Terminal 1 — API**

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

(On macOS/Linux use `python3` if that is your command for Python 3.)

**Terminal 2 — web UI**

```bash
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173** in a browser.

On **Windows**, run **`.\launch.ps1`** or **`launch.bat`** (after **`npm install`** created them) to start both servers and open the browser. You may need to allow script execution in PowerShell. On **macOS/Linux**, **`./launch.sh`** does the same with backend in the background.

---

## More detail

See **[README.md](README.md)** for production builds, API proxy options, data and API keys, and private-repository downloads.
