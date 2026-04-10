# Install from a public download

These steps work for **anyone** with a normal browser. No GitHub account is needed as long as the repository is **Public**.

**Maintainers:** Before sharing, replace `YOUR-GITHUB-USERNAME` everywhere below with your GitHub user or organization name (for example `octocat`). If your repository name is not `PredictionMarketApp`, replace that too. If your default branch is not `main`, change `main` in the download URL.

---

## Shareable links

Send people **one** of these:

| What | Link |
|------|------|
| **This install guide** (GitHub Pages site) | `https://YOUR-GITHUB-USERNAME.github.io/PredictionMarketApp/` |
| **This install guide** (markdown on GitHub) | `https://github.com/YOUR-GITHUB-USERNAME/PredictionMarketApp/blob/main/INSTALL.md` |
| **Download latest source** (`main` branch, always current) | `https://github.com/YOUR-GITHUB-USERNAME/PredictionMarketApp/archive/refs/heads/main.zip` |
| **Download latest release** (same layout; use after you publish at least one version tag) | `https://github.com/YOUR-GITHUB-USERNAME/PredictionMarketApp/releases/latest/download/PredictionMarketApp.zip` |

The **source** and **release** ZIPs contain the same tracked files as a `git clone` (no `node_modules`, no `.venv`, no database).

### GitHub Pages (maintainers)

To serve the styled install page at `https://YOUR-GITHUB-USERNAME.github.io/PredictionMarketApp/`:

1. **Settings** → **Pages** → **Build and deployment** → set **Source** to **GitHub Actions**.
2. Push the `docs/` folder and `.github/workflows/pages.yml` to `main`, or open **Actions** → **Deploy Pages** → **Run workflow**.

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
2. Open the folder that contains **`backend`**, **`frontend`**, and **`requirements.txt`**.  
   GitHub names the folder like `PredictionMarketApp-main` — that is fine; use it as the project root.

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

On **Windows** you can instead run **`.\launch.ps1`** from the project root (starts both servers and opens the browser). You may need to allow script execution in PowerShell.

---

## More detail

See **[README.md](README.md)** for production builds, API proxy options, data and API keys, and private-repository downloads.
