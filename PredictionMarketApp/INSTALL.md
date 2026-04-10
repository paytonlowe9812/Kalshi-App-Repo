# Install

Full monorepo notes: **[README.md](../README.md)** at the repository root.

## Quick steps

1. Download your platform archive from GitHub **Releases** ( **Latest** ), or clone the repo and open this folder (**`PredictionMarketApp/`**).

2. Install **Python 3.10+** and **Node.js 18+** if you do not have them.

3. Run **one** command for your OS (from this folder):

   - **Windows:** **`install.bat`** or **`.\install.ps1`**

   - **macOS / Linux:** **`chmod +x install.sh`** once, then **`./install.sh`**

4. Start the app:

   - **Windows:** **`launch.bat`** or **`.\launch.ps1`**

   - **macOS / Linux:** **`./launch.sh`**

5. Open **http://127.0.0.1:5173**.

---

Maintainers: **`.github/workflows/pages.yml`** at the repo root publishes **`docs/index.html`**. **`.github/workflows/release-zip.yml`** rebuilds platform ZIPs on every push to **`main`** under the single **Latest** release.
