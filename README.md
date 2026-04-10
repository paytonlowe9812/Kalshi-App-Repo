# Kalshi App Repo

All commands below use the **`PredictionMarketApp/`** folder (the one that contains `backend/`, `frontend/`, and `requirements.txt`). If you use a **release** ZIP, that folder is what you unpack. If you **clone** the monorepo, run `cd PredictionMarketApp` first (from the repo root).

## Prerequisites

**Python 3.10+** and **Node.js 18+** (with **npm**). Install those once from [python.org](https://www.python.org/downloads/) and [nodejs.org](https://nodejs.org/) if needed.

## Install

1. Get the app: from GitHub **Releases**, open **Latest** (one rolling release, updated on every push to `main`), and download the archive for your OS — or clone the repo and enter **`PredictionMarketApp/`** as above.

2. Run **one** installer for your system (from inside **`PredictionMarketApp/`**):

   - **Windows:** double-click **`install.bat`**, or in PowerShell run **`.\install.ps1`**.

   - **macOS / Linux:** in a terminal run **`chmod +x install.sh`** once, then **`./install.sh`**.

That creates a Python virtual environment, installs dependencies, runs **`npm install`**, and generates the launch scripts.

## Start the app

Still in **`PredictionMarketApp/`**:

- **Windows:** **`launch.bat`** or **`.\launch.ps1`**

- **macOS / Linux:** **`./launch.sh`**

Open **http://127.0.0.1:5173** in your browser.

---

More detail (production build, API proxy, developers): **[PredictionMarketApp/README.md](PredictionMarketApp/README.md)**.
