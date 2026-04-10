# Kalshi Bot Builder -- Overview Guide

Kalshi Bot Builder is a local desktop application for building, testing, and running
automated trading bots on the [Kalshi](https://kalshi.com) prediction-market exchange.
It pairs a Python backend (FastAPI) with a React frontend, stores all data in a local
SQLite database, and connects to Kalshi over HTTPS and WebSocket for real-time
market data and order execution.

---

## Getting started

1. Run `./install.sh` to install all dependencies and build the frontend.
2. Run `./launch.sh` to start the server.
3. Open **http://127.0.0.1:8080** in your browser.
4. On first launch the app opens the **Settings** tab so you can add a Kalshi API key.

### API keys

- Navigate to **Settings > API Keys** to add one or more key profiles.
- Each key has a name, key ID, RSA private key (PEM), and a **demo / live** toggle.
- Use the **Test** button to verify connectivity before activating a key.
- Only one key can be active at a time. Activating a key reconnects the WebSocket
  and resubscribes to all tracked market tickers.

### Demo vs. live

Keys marked **demo** route all requests to the Kalshi demo environment
(`demo-api.kalshi.co`). Use demo keys while building and testing strategies.

### Sharing this project

This guide does not contain any credentials. Your Kalshi API keys and private key
material are stored only in the local SQLite file **`data/app.db`** on your machine.

Before you send someone a copy of the project folder (zip, cloud drive, git push,
and so on), **delete `data/app.db`** or omit the entire **`data/`** directory.
The recipient runs `./install.sh`, which creates an empty `data/` folder; the app
creates a fresh database on first launch. They add their own keys in Settings.

If you use Git, the included **`.gitignore`** keeps `data/*.db` out of the
repository so keys are not committed by mistake.

---

## Markets

The **Markets** tab lets you browse events listed on Kalshi.

- **Search** by keyword.
- **Filter** by category: Crypto, Politics, Economics, Sports, Weather.
- **Sort** by volume or close date.
- **Favorite** markets for quick access.
- Open a market detail panel to see the current orderbook and price history, or to
  assign the market to an existing bot.

---

## Sentiment indexes

The sentiment strip (visible on desktop at the top of the screen) displays
user-created **indexes** -- named baskets of markets with custom labels.

- Create an index, pick the markets that compose it, and give each one a label.
- The app subscribes to live prices via WebSocket and computes an aggregate
  **sentiment score**, **bull/bear counts**, and per-market yes/no odds.
- Index values are also exposed as **rule variables** so your bots can trade on
  aggregate sentiment (e.g. `CryptoIndex.Score`, `BTC.YES`).

---

## Bots

A bot is an automated agent attached to a single Kalshi market. It runs a loop that
evaluates a set of rules on each tick and executes the first action that fires.

### Creating a bot

- Give it a name and assign a market ticker.
- Optionally place it inside a **group** for organization.
- Toggle **paper trading** to simulate trades without submitting real orders.
- Enable **auto-roll** for short-duration series (e.g. 15-minute crypto contracts);
  when the current contract settles, the bot automatically picks the next one.

### Groups

Groups are folders for bots. They support:

- Drag bots between groups.
- **Start all / Stop all** to control every bot in a group at once.
- **Bulk edit** to change paper mode, trigger, or market for every bot in the group.

### Copying and exporting bots

- **Copy** a bot to duplicate it along with all its rules.
- **Export** all bots as JSON from the Settings tab, or **import** a JSON file to
  restore them.

---

## Rule editor

The **Editor** tab is where you define a bot's decision logic. Rules are evaluated
top to bottom and support the following line types:

| Line type | Purpose |
|-----------|---------|
| **IF** | Start a conditional block. Compare a variable to a value using operators: `=`, `!=`, `>`, `<`, `>=`, `<=`. |
| **AND / OR** | Chain additional conditions onto an IF. |
| **THEN** | The action to take when the preceding condition is true. |
| **ELSE** | The action to take when the condition is false. |
| **GOTO** | Jump to a specific line number (for looping or branching logic). |
| **SET_VAR** | Assign a value to a user-defined variable. |
| **LOG** | Write a message to the trade log. |
| **ALERT** | Write an alert-level message to the trade log. |
| **STOP** | Halt the bot. |
| **CONTINUE** | Skip to the next evaluation cycle. |

### Available actions

When a THEN or ELSE fires, it can execute one of:

- **BUY** -- place a market order (yes or no side).
- **SELL** -- place a market order on the opposite side.
- **LIMIT** -- place a limit order at a specific price.
- **CLOSE** -- close all open positions on the bot's market.
- **SET_VAR**, **LOG**, **ALERT**, **STOP** -- as described above.

### Rule snapshots

Save the current rule set as a named **snapshot** at any time. You can browse
saved snapshots in the sidebar and **restore** any previous version with one click.

---

## Variables

Rules reference variables by name. The engine resolves them in this order
(later sources override earlier ones):

1. **Market variables** (live from WebSocket or REST):
   `YES_price`, `NO_price`, `last_price`, `yes_bid`, `yes_ask`, `no_bid`,
   `no_ask`, `volume`.

2. **Portfolio variables**:
   `DailyPnL`, `PositionSize`.

3. **Sentiment index variables** (per index you have created):
   `{IndexName}.Score`, `{IndexName}.BullCount`, `{IndexName}.BearCount`,
   `{IndexName}.AvgYES`, `{IndexName}.AvgNO`, and per-constituent
   `{Label}.YES`, `{Label}.NO`.

4. **User-defined variables**: Set via the Variables panel or the SET_VAR action.
   These persist in the database between bot restarts.

---

## Simulator

The **SIM** tab (desktop) lets you dry-run a bot's rules without placing any orders.

- Adjust variable values with sliders to model different market conditions.
- Choose a playback speed (fast, medium, slow) or step through manually.
- The simulator walks through every rule line and shows which conditions matched,
  which action would fire, and the final variable state.
- An infinite-loop guard stops evaluation after 100 visits to the same line.

---

## Portfolio and P&L

The **P&L** tab shows your trading performance:

- **Total value** -- your current Kalshi account balance.
- **Today's P&L** -- net profit or loss from today's trades.
- **Win rate** -- percentage of trades with positive P&L.
- **Best / worst day** -- historical extremes.
- **Chart** -- line or bar chart of daily P&L, viewable for today or a custom date range.
  Optionally break down by individual bot.

---

## Trade log

The **Log** tab is a searchable, filterable history of every action your bots have taken.

- Filter by bot, action type, market, or date range.
- Entries are grouped by day for readability.
- Export the log as **CSV** or **JSON** with optional date-range filtering.

---

## Risk management

Available in **Settings > Risk**:

| Control | Description |
|---------|-------------|
| **Daily loss limit** | Stops all bots if cumulative daily P&L exceeds a threshold. |
| **Window exposure cap** | Limits total contracts traded in a rolling 15-minute window. |
| **Circuit breaker** | Halts trading when recent trades show high entry prices and negative P&L. |
| **Max open positions** | Caps the number of simultaneous open positions. |
| **Trading schedule** | Restrict bot execution to specific hours per day of the week. |

### Panic button

The **Panic** button in Settings immediately stops every running bot and submits
market-close orders for all open positions.

---

## Paper trading

Paper trading can be enabled globally (in Settings) or per-bot.

- When active, the top navigation bar displays a **Paper Mode** banner.
- All bot actions are logged normally but no orders are sent to Kalshi.
- Use paper mode alongside the simulator to validate strategies before going live.

---

## Architecture summary

```
Browser (http://127.0.0.1:8080)
   |
   v
FastAPI backend (port 8080)
   |-- REST API (/api/...)
   |-- Serves built React frontend (/)
   |-- SQLite database (data/app.db)
   |-- WebSocket connection to Kalshi (live prices)
   |-- HTTPS to Kalshi (orders, market data)
```

All data stays local on your machine. The only outbound connections are to Kalshi's
API servers and (optionally) Gumroad for license validation.
