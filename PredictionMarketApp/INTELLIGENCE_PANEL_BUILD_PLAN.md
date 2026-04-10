# Intelligence Panel — Build Plan
> An addendum to the core Kalshi Bot Builder spec.
> This document covers the Intelligence Panel, Watch system, Signal architecture,
> and how they integrate with the existing rule engine and bot executor.

---

## What This Actually Is

Before specs and endpoints — a clear statement of intent.

The Intelligence Panel is not a dashboard. It is the **perception layer** of a trading operating system. It watches the world — prediction markets, news, sentiment, economic events — and distills everything into named Signals. Those Signals flow directly into the rule engine as variables. Bots act on them. The loop closes.

The architecture has three layers:

```
WORLD                    INTELLIGENCE PANEL              BOT ENGINE
─────────────────        ──────────────────────          ──────────────
Kalshi                   Watches (configurable)          Rule evaluator
Polymarket        ──►    Data layers (per Watch)  ──►    SIGNAL variables
Metaculus                Orb score (0-100)               Bot execution
Manifold                 Signal emission                 Trade actions
PredictIt                Arbitrage detection             Kalshi API
News / Social            Cross-platform matching
Economic calendar
```

Everything in this document is **additive** to the existing BUILD_SPEC.md.
All existing components, endpoints, and database tables remain unchanged.

---

## Table of Contents

1. [New Database Tables](#1-new-database-tables)
2. [Watch System](#2-watch-system)
3. [Signal Architecture](#3-signal-architecture)
4. [Data Layer Integrations](#4-data-layer-integrations)
5. [Arbitrage Engine](#5-arbitrage-engine)
6. [Cross-Platform Market Matching](#6-cross-platform-market-matching)
7. [Backend API Endpoints](#7-backend-api-endpoints)
8. [Frontend Components](#8-frontend-components)
9. [Integration with Rule Engine](#9-integration-with-rule-engine)
10. [Build Order](#10-build-order)

---

## 1. New Database Tables

### 1.1 `watches`
```sql
CREATE TABLE IF NOT EXISTS watches (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  name            TEXT NOT NULL,
  anchor_type     TEXT NOT NULL,
  -- event | market | keyword | entity | category
  anchor_value    TEXT NOT NULL,
  -- the thing being watched: event description, ticker, keyword, person name, category
  platforms       TEXT NOT NULL,
  -- JSON array: ["kalshi","polymarket","metaculus","manifold","predictit","smarkets","betfair"]
  active_layers   TEXT NOT NULL,
  -- JSON array: ["prices","arbitrage","consensus","news","social","econ_events","volume","movement"]
  arb_threshold   REAL DEFAULT 0.05,
  -- minimum spread % to consider an arbitrage active (0.05 = 5%)
  orb_score       REAL DEFAULT 0,
  -- last computed composite significance score 0-100
  orb_level       TEXT DEFAULT 'cold',
  -- cold | warm | hot | critical
  pinned          INTEGER DEFAULT 0,
  collapsed       INTEGER DEFAULT 0,
  size            TEXT DEFAULT 'medium',
  -- small | medium | large
  sort_order      INTEGER DEFAULT 0,
  group_id        INTEGER REFERENCES watch_groups(id),
  last_computed   TEXT,
  created_at      TEXT DEFAULT (datetime('now'))
);
```

### 1.2 `watch_groups`
```sql
CREATE TABLE IF NOT EXISTS watch_groups (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL,
  collapsed  INTEGER DEFAULT 0,
  sort_order INTEGER DEFAULT 0
);
```

### 1.3 `watch_platform_markets`
Links a Watch to the specific market tickers on each platform that
represent the same event. Populated by the AI matching engine + user confirmation.

```sql
CREATE TABLE IF NOT EXISTS watch_platform_markets (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  watch_id     INTEGER NOT NULL REFERENCES watches(id) ON DELETE CASCADE,
  platform     TEXT NOT NULL,
  -- kalshi | polymarket | metaculus | manifold | predictit | smarkets | betfair
  ticker       TEXT NOT NULL,
  -- platform-specific market ID or ticker
  market_title TEXT,
  yes_price    REAL,
  -- last fetched YES probability (0-100)
  no_price     REAL,
  volume       REAL,
  confirmed    INTEGER DEFAULT 0,
  -- 0 = AI suggested, 1 = user confirmed
  last_fetched TEXT,
  UNIQUE(watch_id, platform)
);
```

### 1.4 `signals`
Global signal registry. Signals are defined here and available as
variables in every bot's rule engine.

```sql
CREATE TABLE IF NOT EXISTS signals (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  watch_id     INTEGER REFERENCES watches(id) ON DELETE CASCADE,
  name         TEXT NOT NULL UNIQUE,
  -- the variable name used in rule engine: e.g. "BTC_ARB"
  signal_type  TEXT NOT NULL,
  -- continuous | boolean | event
  value        REAL DEFAULT 0,
  -- current value (spread %, score, 0/1 etc.)
  is_active    INTEGER DEFAULT 0,
  -- whether the signal is currently firing
  description  TEXT,
  -- human-readable description shown in VariablePicker
  threshold    REAL,
  -- value at which is_active flips to 1
  last_fired   TEXT,
  -- when was is_active last true
  created_at   TEXT DEFAULT (datetime('now'))
);
```

### 1.5 `signal_history`
Time-series log of signal values. Used for sparklines and signal
trend analysis in the expanded Watch view.

```sql
CREATE TABLE IF NOT EXISTS signal_history (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id  INTEGER NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
  value      REAL NOT NULL,
  is_active  INTEGER DEFAULT 0,
  recorded_at TEXT DEFAULT (datetime('now'))
);
```

### 1.6 `watch_news_cache`
Cached news items fetched for each Watch. Refreshed periodically.

```sql
CREATE TABLE IF NOT EXISTS watch_news_cache (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  watch_id   INTEGER NOT NULL REFERENCES watches(id) ON DELETE CASCADE,
  headline   TEXT NOT NULL,
  source     TEXT,
  url        TEXT,
  published_at TEXT,
  fetched_at TEXT DEFAULT (datetime('now'))
);
```

### 1.7 `platform_credentials`
API keys and config for external prediction market platforms.
Unlike Kalshi keys (in `api_keys`), these cover other platforms.

```sql
CREATE TABLE IF NOT EXISTS platform_credentials (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  platform    TEXT NOT NULL UNIQUE,
  api_key     TEXT,
  api_secret  TEXT,
  wallet_addr TEXT,
  -- for Polymarket (uses wallet-based auth)
  enabled     INTEGER DEFAULT 1,
  last_tested TEXT
);
```

---

## 2. Watch System

### 2.1 Watch Anchor Types

A Watch is anchored to one of five things. The anchor type determines
how the system finds related markets across platforms.

| Anchor Type | Example | Matching Strategy |
|---|---|---|
| `event` | "BTC above $100k by April" | AI matches markets with similar title + expiry |
| `market` | Specific Kalshi ticker | User manually links equivalents on other platforms |
| `keyword` | "Fed rate cut" | Text search across all platform market titles |
| `entity` | "Trump", "Elon Musk" | Named entity recognition across market titles |
| `category` | "all crypto markets" | Platform category filter + keyword filter |

### 2.2 Data Layers

Each Watch has a set of toggleable data layers. Each layer contributes
to the orb score with a configurable weight.

| Layer | What it does | Default weight |
|---|---|---|
| `prices` | Fetches YES/NO from all linked platforms | 25% |
| `arbitrage` | Computes spread, detects arb opportunity | 30% |
| `consensus` | Weighted average probability across platforms | 15% |
| `news` | Fetches headlines matching anchor via news API | 15% |
| `social` | Reddit/Twitter sentiment score for anchor | 10% |
| `econ_events` | Upcoming scheduled events relevant to anchor | 5% |

### 2.3 Orb Score Calculation

The orb score (0–100) is a weighted composite of all active layers.
Computed every loop interval in the background.

```python
def compute_orb_score(watch: Watch) -> tuple[float, str]:
    score = 0.0
    layers = watch.active_layers

    if 'arbitrage' in layers:
        arb = get_arb_spread(watch)
        # arb of 10%+ = full 30 points
        score += min(arb / 0.10, 1.0) * 30

    if 'prices' in layers:
        movement = get_recent_price_movement(watch)
        # movement of 15%+ in 1h = full 25 points
        score += min(movement / 0.15, 1.0) * 25

    if 'news' in layers:
        recency_score = get_news_recency_score(watch)
        # score 0-1 based on how recent and numerous the news is
        score += recency_score * 15

    if 'social' in layers:
        sentiment_spike = get_social_spike_score(watch)
        score += sentiment_spike * 10

    if 'consensus' in layers:
        divergence = get_consensus_divergence(watch)
        # platforms disagreeing = more significant
        score += divergence * 15

    if 'econ_events' in layers:
        proximity = get_econ_event_proximity(watch)
        # event in next 24h = full 5 points
        score += proximity * 5

    # Determine level
    if score >= 80:
        level = 'critical'
    elif score >= 55:
        level = 'hot'
    elif score >= 30:
        level = 'warm'
    else:
        level = 'cold'

    return round(score), level
```

---

## 3. Signal Architecture

### 3.1 Signal Types

Three signal types, matching what the rule engine needs:

| Type | Behavior | Rule engine usage |
|---|---|---|
| `continuous` | A live numeric value updated every loop | `IF SIGNAL.BTC_ARB > 8` |
| `boolean` | True/false flag, active when threshold crossed | `IF SIGNAL.BTC_ARB_ACTIVE = 1` |
| `event` | One-shot fire when condition first becomes true | Bot trigger type: "Fired by signal" |

Every Signal automatically gets **three variables** in the rule engine:

```
SIGNAL.[name]         → current numeric value (continuous)
SIGNAL.[name].ACTIVE  → 1 if active, 0 if not (boolean)
SIGNAL.[name].SCORE   → orb score of parent Watch (0-100)
```

Example — a Signal named `BTC_ARB` gives the bot:
```
SIGNAL.BTC_ARB          = 11.3   (current spread %)
SIGNAL.BTC_ARB.ACTIVE   = 1      (above threshold)
SIGNAL.BTC_ARB.SCORE    = 87     (parent Watch orb score)
```

### 3.2 Signal Update Loop

Runs as a background asyncio task, separate from the bot executor.

```python
async def signal_update_loop():
    while True:
        watches = db.get_all_watches()
        for watch in watches:
            # 1. Fetch fresh data for all active layers
            data = await fetch_watch_data(watch)

            # 2. Compute orb score
            score, level = compute_orb_score(watch)
            db.update_watch_score(watch.id, score, level)

            # 3. Update all signals attached to this watch
            for signal in db.get_signals_for_watch(watch.id):
                new_value = compute_signal_value(signal, data)
                was_active = signal.is_active
                is_active = new_value >= signal.threshold

                db.update_signal(signal.id, new_value, is_active)

                # 4. Log to history (for sparklines)
                db.log_signal_history(signal.id, new_value, is_active)

                # 5. If event-type signal just became active — fire it
                if signal.signal_type == 'event' and is_active and not was_active:
                    await fire_event_signal(signal)

        await asyncio.sleep(get_loop_interval())
```

### 3.3 Signal Variables in the Rule Engine

In `variables.py`, add a new resolution block:

```python
# Intelligence Signals
for signal in db.get_all_signals():
    variables[f'SIGNAL.{signal.name}'] = signal.value
    variables[f'SIGNAL.{signal.name}.ACTIVE'] = 1 if signal.is_active else 0
    variables[f'SIGNAL.{signal.name}.SCORE'] = db.get_watch_score(signal.watch_id)
```

In `VariablePicker.jsx`, add a new grouped section:

```
Market Data        → existing
Portfolio          → existing
Sentiment Indexes  → existing
User Variables     → existing
────────────────────────────
Intelligence Signals  ← NEW
  SIGNAL.BTC_ARB              current: 11.3
  SIGNAL.BTC_ARB.ACTIVE       current: 1
  SIGNAL.BTC_ARB.SCORE        current: 87
  SIGNAL.FED_CUT              current: 3.2
  ...
```

Each Signal variable in the picker shows:
- Signal name
- Current live value as a tooltip
- Parent Watch name in muted text
- A colored dot matching the Watch's orb level

---

## 4. Data Layer Integrations

### 4.1 Platform API Clients

Each platform needs its own client in `backend/platforms/`.

```
backend/
└── platforms/
    ├── base.py          # Abstract base class all clients implement
    ├── kalshi.py        # Already exists — move/alias from kalshi/client.py
    ├── polymarket.py    # REST + CLOB API
    ├── metaculus.py     # REST API (public, no auth required)
    ├── manifold.py      # REST API (public)
    ├── predictit.py     # REST API
    ├── smarkets.py      # REST API
    └── betfair.py       # REST API (requires account)
```

Base class interface every platform client must implement:

```python
class PredictionPlatform:
    platform_id: str          # "kalshi" | "polymarket" etc.
    display_name: str         # "Kalshi" | "Polymarket" etc.
    requires_auth: bool

    async def search_markets(self, query: str) -> list[MarketResult]:
        """Search for markets matching a query string."""
        ...

    async def get_market(self, ticker: str) -> MarketDetail:
        """Get current price and metadata for a specific market."""
        ...

    async def get_yes_price(self, ticker: str) -> float:
        """Return current YES probability as 0-100."""
        ...
```

### 4.2 News Integration

Use a free news API for headline fetching. Recommended: **NewsAPI.org**
(free tier: 100 requests/day) or **GNews API** (free tier: 100/day).

```python
# backend/intelligence/news.py

async def fetch_news_for_watch(watch: Watch) -> list[NewsItem]:
    query = build_news_query(watch)
    # query derived from anchor_value + anchor_type
    # e.g. entity watch "Trump" → query = "Trump prediction market"
    # e.g. keyword watch "Fed rate cut" → query = "Federal Reserve rate cut"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "sortBy": "publishedAt",
                "pageSize": 5,
                "apiKey": settings.get("newsapi_key")
            }
        )
    return parse_news_response(resp.json())
```

News API key stored in `settings` table as `newsapi_key`.
User enters it in the Settings screen under a new "Intelligence" section.

### 4.3 Social Sentiment Integration

**Reddit:** Use the public Reddit JSON API (no auth required).
```
GET https://www.reddit.com/search.json?q={query}&sort=new&limit=25
```
Parse post count, upvote ratio, and comment velocity to produce a 0–1 sentiment score.

**Twitter/X:** Requires API v2 bearer token (free tier available).
Store as `twitter_bearer_token` in settings.

Sentiment score formula:
```python
def compute_social_score(posts: list) -> float:
    if not posts: return 0.0
    recency_weight = posts_in_last_hour / total_posts
    sentiment = average_upvote_ratio(posts)
    volume = min(len(posts) / 50, 1.0)  # normalize to 0-1 at 50+ posts
    return (recency_weight * 0.4 + sentiment * 0.3 + volume * 0.3)
```

### 4.4 Economic Calendar

Use **TradingEconomics API** (free tier) or scrape the **Fed calendar**
directly since it's public.

Events to track:
- CPI release
- FOMC meeting / Fed rate decision
- Jobs report (NFP)
- GDP release
- Any event matching the Watch's anchor keywords

Store upcoming events in a simple `econ_events` cache table.
Proximity score: 1.0 if event in next 6 hours, declining to 0.0 at 7+ days.

---

## 5. Arbitrage Engine

### 5.1 Core Calculation

```python
# backend/intelligence/arbitrage.py

def compute_arbitrage(watch: Watch, markets: list[WatchPlatformMarket]) -> ArbResult:
    """
    For a binary market (YES/NO), true arbitrage exists when:
    cost of YES on cheapest platform + cost of NO on cheapest platform < $1.00

    Example:
    Kalshi YES = 72¢, Polymarket YES = 61¢
    Buy YES on Polymarket (61¢) + NO on Kalshi (28¢) = 89¢ total
    Guaranteed $1 payout → 11¢ profit per contract
    """
    if len(markets) < 2:
        return ArbResult(exists=False, spread=0)

    # Find cheapest YES and cheapest NO across all platforms
    cheapest_yes = min(markets, key=lambda m: m.yes_price)
    cheapest_no = min(markets, key=lambda m: m.no_price)

    # Can't use same platform for both legs (usually)
    if cheapest_yes.platform == cheapest_no.platform:
        # Find next cheapest on other platform
        other_markets = [m for m in markets if m.platform != cheapest_yes.platform]
        if not other_markets:
            return ArbResult(exists=False, spread=0)
        cheapest_no = min(other_markets, key=lambda m: m.no_price)

    total_cost = cheapest_yes.yes_price + cheapest_no.no_price
    profit_per_contract = 100 - total_cost  # in cents
    spread_pct = profit_per_contract / 100

    return ArbResult(
        exists=profit_per_contract > 0,
        spread_pct=spread_pct,
        spread_cents=profit_per_contract,
        buy_yes_platform=cheapest_yes.platform,
        buy_yes_price=cheapest_yes.yes_price,
        buy_no_platform=cheapest_no.platform,
        buy_no_price=cheapest_no.no_price,
        total_cost_cents=total_cost,
        profit_cents=profit_per_contract,
        near_arb=spread_pct > -0.05  # within 5% of being true arb
    )
```

### 5.2 Near-Arbitrage

Even when true arb doesn't exist, show "near-arb" when spread > user-set threshold.
This surfaces high-value trading opportunities even if not mathematically guaranteed.

### 5.3 Arbitrage Signal

When a Watch has arbitrage enabled, it automatically creates a signal:
```
SIGNAL.[WatchName]_ARB       = current spread % (e.g. 11.3)
SIGNAL.[WatchName]_ARB.ACTIVE = 1 when spread > watch.arb_threshold
```

---

## 6. Cross-Platform Market Matching

The hardest problem: knowing that Kalshi's "Will BTC close above $100k on April 30?"
is the same event as Polymarket's "Bitcoin above 100k USD by end of April?".

### 6.1 Matching Pipeline

```python
# backend/intelligence/matcher.py

async def find_matching_markets(watch: Watch) -> list[MarketMatch]:
    """
    Multi-stage matching pipeline.
    Returns suggested matches for user confirmation.
    """
    suggestions = []

    for platform in watch.platforms:
        client = get_platform_client(platform)

        # Stage 1: Keyword search on platform API
        results = await client.search_markets(watch.anchor_value)

        # Stage 2: Score each result by similarity
        for result in results:
            score = compute_similarity_score(watch.anchor_value, result.title)
            if score > 0.6:  # 60% similarity threshold
                suggestions.append(MarketMatch(
                    platform=platform,
                    ticker=result.ticker,
                    title=result.title,
                    similarity_score=score,
                    confirmed=False  # user must confirm
                ))

    # Stage 3: AI re-ranking (optional, uses Claude API if enabled)
    if settings.get('ai_matching_enabled') == 'true':
        suggestions = await ai_rerank_matches(watch, suggestions)

    return sorted(suggestions, key=lambda m: m.similarity_score, reverse=True)
```

### 6.2 Similarity Scoring

```python
def compute_similarity_score(query: str, title: str) -> float:
    query_tokens = set(query.lower().split())
    title_tokens = set(title.lower().split())

    # Remove stop words
    stop_words = {'the','a','an','is','will','by','on','above','below','in','at'}
    query_tokens -= stop_words
    title_tokens -= stop_words

    # Jaccard similarity
    intersection = query_tokens & title_tokens
    union = query_tokens | title_tokens
    if not union:
        return 0.0
    return len(intersection) / len(union)
```

### 6.3 User Confirmation Flow

When a Watch is created:
1. AI suggests matched markets per platform (shown as "AI suggested" chips)
2. User reviews suggestions in a confirmation modal
3. User confirms or rejects each suggestion
4. Confirmed matches are stored in `watch_platform_markets` with `confirmed = 1`
5. Watch begins fetching live prices from confirmed markets only

---

## 7. Backend API Endpoints

### Watches — `/api/intelligence/watches`

| Method | Path | Description |
|---|---|---|
| GET | `/api/intelligence/watches` | All watches with current orb scores and signal values |
| POST | `/api/intelligence/watches` | Create watch `{ name, anchor_type, anchor_value, platforms, active_layers, arb_threshold }` |
| GET | `/api/intelligence/watches/{id}` | Single watch with full detail (all layer data) |
| PUT | `/api/intelligence/watches/{id}` | Update watch config |
| DELETE | `/api/intelligence/watches/{id}` | Delete watch + all linked signals |
| POST | `/api/intelligence/watches/{id}/pin` | Toggle pinned |
| PUT | `/api/intelligence/watches/reorder` | Update sort_order for drag-drop |

### Market Matching — `/api/intelligence/matches`

| Method | Path | Description |
|---|---|---|
| POST | `/api/intelligence/matches/suggest` | Suggest market matches for a watch `{ watch_id }` |
| POST | `/api/intelligence/matches/confirm` | Confirm a suggested match `{ watch_id, platform, ticker }` |
| DELETE | `/api/intelligence/matches/{id}` | Remove a platform link from a watch |

### Signals — `/api/intelligence/signals`

| Method | Path | Description |
|---|---|---|
| GET | `/api/intelligence/signals` | All signals with current values (used by rule engine) |
| POST | `/api/intelligence/signals` | Create signal `{ watch_id, name, signal_type, threshold, description }` |
| PUT | `/api/intelligence/signals/{id}` | Update signal config |
| DELETE | `/api/intelligence/signals/{id}` | Delete signal (removes from rule engine) |
| GET | `/api/intelligence/signals/{id}/history` | Time-series history for sparklines |

### Watch Groups — `/api/intelligence/groups`

| Method | Path | Description |
|---|---|---|
| GET | `/api/intelligence/groups` | All groups with watches |
| POST | `/api/intelligence/groups` | Create group |
| PUT | `/api/intelligence/groups/{id}` | Rename or reorder |
| DELETE | `/api/intelligence/groups/{id}` | Delete group |

### Platform Credentials — `/api/intelligence/platforms`

| Method | Path | Description |
|---|---|---|
| GET | `/api/intelligence/platforms` | All platform configs (keys redacted) |
| PUT | `/api/intelligence/platforms/{platform}` | Update credentials for a platform |
| POST | `/api/intelligence/platforms/{platform}/test` | Test connection |

---

## 8. Frontend Components

### New files to add to the existing component tree:

```
frontend/src/components/
└── Intelligence/
    ├── IntelligencePanel.jsx       # Main tab content — grid of watches
    ├── WatchGrid.jsx               # Drag-drop grid layout manager
    ├── WatchGroup.jsx              # Labeled group section
    ├── WatchCard.jsx               # Single watch card (collapsed + expanded)
    ├── WatchOrb.jsx                # The orb — score, color, pulse
    ├── WatchCollapsed.jsx          # Collapsed card body (orb + 3-4 stats)
    ├── WatchExpanded.jsx           # Expanded card body (all layers)
    ├── layers/
    │   ├── PriceLayer.jsx          # Platform price comparison bars
    │   ├── ArbLayer.jsx            # Arbitrage opportunity box + calculator
    │   ├── ConsensusLayer.jsx      # Weighted average across platforms
    │   ├── NewsLayer.jsx           # Filtered news feed
    │   ├── SocialLayer.jsx         # Reddit/Twitter sentiment
    │   └── EconLayer.jsx           # Economic event countdowns
    ├── CreateWatchModal.jsx        # Watch creation flow
    ├── MatchConfirmModal.jsx       # AI market match confirmation
    ├── SignalBuilder.jsx           # Create/configure a signal from a Watch
    └── PlatformSettings.jsx        # API key management for external platforms
```

### 8.1 `WatchCard.jsx` — Key behaviors

**Collapsed state** (always visible):
```
[ORB: 87 / critical]  [Watch name]              [badge: Arbitrage]
                       [Driver text: top signal driving orb score]
[stat] [stat] [stat]  ← 3 most relevant stats for this watch type
[▼ expand]
```

**Expanded state** (click to toggle):
- Renders only the active data layers for this watch
- Each layer is a `<LayerComponent />` that fetches its own data
- "Create Signal" button at the bottom of every expanded card
- Layer toggle chips: click to enable/disable layers without leaving the card

**Orb component (`WatchOrb.jsx`)**:
```jsx
// Score 0-100 → color + pulse + label
// 0-29:  cold     → blue bg, no pulse
// 30-54: warm     → amber bg, no pulse
// 55-79: hot      → coral bg, slow pulse
// 80-100: critical → red bg, fast pulse

const orbLevel = (score) => {
  if (score >= 80) return { label: 'critical', color: 'red', pulse: 'fast' }
  if (score >= 55) return { label: 'hot',      color: 'coral', pulse: 'slow' }
  if (score >= 30) return { label: 'warm',     color: 'amber', pulse: 'none' }
  return              { label: 'cold',     color: 'blue',  pulse: 'none' }
}
```

### 8.2 `ArbLayer.jsx` — Arbitrage detail

Shows:
1. All platform prices in a comparison table
2. Arb opportunity box (if spread > threshold):
   - "Buy YES on [Platform] at [X]¢"
   - "Buy NO on [Platform] at [Y]¢"
   - "Total cost: [X+Y]¢ — Profit: [100-(X+Y)]¢ per contract"
3. Simple calculator: "If I trade [N] contracts → profit $[N * profit_cents / 100]"

### 8.3 `CreateWatchModal.jsx` — Watch creation flow

Step 1: Name + anchor
- Name field (text)
- Anchor type selector (event / market / keyword / entity / category)
- Anchor value field (changes label based on type)

Step 2: Platforms
- Checkboxes for all 7 platforms
- Shows connection status (green = connected, gray = not configured)
- Link to platform settings for unconfigured platforms

Step 3: Layers
- Toggle switches for each data layer
- Arb threshold slider (shown only if arbitrage layer enabled)

Step 4: Match confirmation (async — AI runs in background)
- Shows suggested market matches per platform
- Each suggestion: platform name, market title, similarity score, confirm/reject
- "Skip for now" option — can confirm later in Watch settings

Step 5: Signal setup (optional)
- "Create a signal from this Watch?" toggle
- Signal name field (auto-suggested from Watch name)
- Signal type: continuous / boolean / event
- Threshold field

### 8.4 `SignalBuilder.jsx` — Create signal from Watch

Accessible from:
- "Create Signal" button in expanded Watch card
- Step 5 of Watch creation modal
- Signals management screen

Fields:
- Signal name (becomes the variable name in rule engine)
  - Must be alphanumeric + underscores only
  - Auto-uppercased: `btc arb` → `BTC_ARB`
- Signal type: continuous | boolean | event
- Threshold: value at which signal becomes active
- Description: shown in VariablePicker tooltip

Preview panel shows the three variable names that will be
available in the rule editor:
```
SIGNAL.BTC_ARB          → the current spread value
SIGNAL.BTC_ARB.ACTIVE   → 1 when spread > threshold
SIGNAL.BTC_ARB.SCORE    → parent Watch orb score (0-100)
```

---

## 9. Integration with Rule Engine

### 9.1 No changes to rule line types

Signals appear in the **VariablePicker** as a new group.
No new line types needed. The existing `IF [VAR] [OP] [VAR]` structure
handles all signal conditions naturally:

```
IF  SIGNAL.BTC_ARB  >  8          ← spread exceeds 8%
IF  SIGNAL.BTC_ARB.ACTIVE  =  1   ← signal is firing
IF  SIGNAL.FED_CUT.SCORE  >  60   ← Watch orb score above 60
```

### 9.2 Event-type signals as bot triggers

In the bot creation / edit flow, add a new trigger type option:

```
Trigger type:
  ○ Loop (every N seconds)     ← existing
  ○ Price event                ← existing
  ○ Time-based                 ← existing
  ○ Manual                     ← existing
  ● Signal event               ← NEW
      Signal: [SIGNAL.BTC_ARB ▾]
      Fires when: signal becomes active
```

When a signal-triggered bot's signal fires, the executor
immediately runs one evaluation of that bot's rules —
bypassing the normal loop interval.

### 9.3 VariablePicker additions

```jsx
// In VariablePicker.jsx — add new group section
{
  group: 'Intelligence Signals',
  icon: '◈',
  variables: signals.flatMap(signal => [
    {
      name: `SIGNAL.${signal.name}`,
      description: signal.description,
      currentValue: signal.value,
      watchName: signal.watch_name,
      orbLevel: signal.orb_level
    },
    {
      name: `SIGNAL.${signal.name}.ACTIVE`,
      description: `1 when ${signal.name} is active, 0 otherwise`,
      currentValue: signal.is_active ? 1 : 0,
    },
    {
      name: `SIGNAL.${signal.name}.SCORE`,
      description: `Orb score of parent Watch (0-100)`,
      currentValue: signal.watch_score,
    }
  ])
}
```

---

## 10. Build Order

This feature is built **after** the core app (Weeks 1–8 in the main spec).
The Intelligence Panel is Weeks 9–13.

### Week 9 — Platform clients + data foundation

- [ ] Build `base.py` platform interface
- [ ] Implement `polymarket.py` client (public API, no auth needed to start)
- [ ] Implement `metaculus.py` client (fully public API)
- [ ] Implement `manifold.py` client (fully public API)
- [ ] New database tables (watches, signals, watch_platform_markets, etc.)
- [ ] Basic `GET/POST /api/intelligence/watches` endpoints
- [ ] Intelligence tab in top nav (empty state with "Create Watch" prompt)

### Week 10 — Watch creation + market matching

- [ ] `CreateWatchModal.jsx` — full 5-step flow
- [ ] `matcher.py` — keyword similarity matching
- [ ] `MatchConfirmModal.jsx` — AI suggestion confirmation UI
- [ ] `WatchCard.jsx` — collapsed card with orb
- [ ] `WatchOrb.jsx` — color, score, pulse animation
- [ ] `WatchGrid.jsx` — drag-drop layout (use `react-beautiful-dnd`)
- [ ] Pinning, collapsing, resizing watches
- [ ] Watch groups with collapsible sections

### Week 11 — Data layers + orb score

- [ ] `PriceLayer.jsx` — platform price comparison
- [ ] `ArbLayer.jsx` + `arbitrage.py` — arb detection and calculator
- [ ] `ConsensusLayer.jsx` — weighted average display
- [ ] `NewsLayer.jsx` + news API integration
- [ ] Orb score computation (`compute_orb_score`)
- [ ] Background signal update loop
- [ ] `signal_history` logging + sparklines

### Week 12 — Signals + rule engine integration

- [ ] `signals` table + signal CRUD endpoints
- [ ] `SignalBuilder.jsx` — create signal from Watch
- [ ] Signal variables in `variables.py` resolver
- [ ] Signal group in `VariablePicker.jsx`
- [ ] Signal-triggered bot trigger type
- [ ] Event signal firing in executor
- [ ] End-to-end test: Watch detects arb → signal fires → bot buys on Kalshi

### Week 13 — Remaining platforms + polish

- [ ] `predictit.py`, `smarkets.py`, `betfair.py` clients
- [ ] `SocialLayer.jsx` + Reddit sentiment integration
- [ ] `EconLayer.jsx` + economic calendar integration
- [ ] `PlatformSettings.jsx` in Settings screen
- [ ] AI market matching (optional Claude API call)
- [ ] Notification system for signal alerts
- [ ] Full end-to-end test across all platforms

---

## Appendix: External API Summary

| Service | Auth required | Free tier | Purpose |
|---|---|---|---|
| Polymarket | No (read) / Wallet (trade) | Yes | Market prices |
| Metaculus | No | Yes | Market prices |
| Manifold | No | Yes | Market prices |
| PredictIt | No (read) | Yes | Market prices |
| Smarkets | API key | Limited | Market prices |
| Betfair | API key + account | No | Market prices |
| NewsAPI.org | API key | 100 req/day | Headlines |
| Reddit JSON | No | Yes | Social sentiment |
| Twitter API v2 | Bearer token | 500k reads/month | Social sentiment |
| TradingEconomics | API key | Limited | Econ calendar |

*All API keys stored in `settings` table. Entered by user in Settings → Intelligence section.*

---

*Intelligence Panel Build Plan — Addendum to BUILD_SPEC.md — April 2026*
