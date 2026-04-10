# Install from a public download

**Primary install guide:** **[README.md](../README.md)** at the repository root (monorepo paths and full setup). This file repeats the dependency and run commands for the **PredictionMarketApp/** folder only.

These steps work for **anyone** with a normal browser. No GitHub account is needed as long as the repository is **Public**.

**Download the app:** on GitHub open **Releases**, choose **Latest**, and download **`PredictionMarketApp-Windows.zip`**, **`PredictionMarketApp-macOS.tar.gz`**, or **`PredictionMarketApp-Linux.tar.gz`** (created when a maintainer pushes a version tag). Release archives match a `git clone` of the app tree (no `node_modules`, no `.venv`, no database).

### GitHub Pages (maintainers)

To serve this page as a styled site:

1. **Settings** → **Pages** → **Build and deployment** → set **Source** to **GitHub Actions**.
2. **`.github/workflows/pages.yml`** must exist at the **repository root** (next to `PredictionMarketApp/`). Push to `main`, or open **Actions** → **Deploy Pages** → **Run workflow**.

---

## Make the repository public (maintainers)

1. On GitHub: **Settings** → **General** → **Danger Zone** → **Change repository visibility** → **Public**.
2. Push a version tag once so the **latest release** link works, for example:

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

   The workflow attaches **Windows** (`.zip`), **macOS** (`.tar.gz`), and **Linux** (`.tar.gz`) archives under **Latest** on the **Releases** page. Each download includes a small **`PredictionMarketApp/.release-platform`** file (one line) so all three assets upload reliably; you may delete it after unpacking.

---

## After downloading

1. Unzip the file.
2. Open the folder that contains **`backend`**, **`frontend`**, and **`requirements.txt`** (the **project root** for install commands).
   - If you downloaded the **full repository** ZIP, you may see a top folder like `Kalshi-App-Repo-main`, then open **`PredictionMarketApp`** inside it.
   - If you downloaded a **release** archive (`.zip` on Windows, `.tar.gz` on macOS/Linux), extract it, then open the **`PredictionMarketApp`** folder inside (that is the project root).
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

See the repository root **[README.md](../README.md)** for the canonical install walkthrough, and **[README.md](README.md)** in this folder for production builds, API proxy options, data and API keys, and private-repository downloads.
