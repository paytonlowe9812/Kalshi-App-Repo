# Complete Ruleset Builder Instructional Guide

This guide explains every visible control and workflow in the ruleset builder, from selecting a bot to building, reordering, simulating, snapshotting, and maintaining rule logic.

---

## 1) How to Enter the Ruleset Builder

1. Open the `BOTS` tab from the bottom navigation.
2. Select a bot row (checkbox or row context) so bot-level actions appear.
3. Click the bot-level `EDIT` action (or the bottom `EDIT` tab if a bot is already active).

### Screenshot - Bot Registry and Bot Selection

![Bot registry and selecting a bot](file:///C:/Users/pman/AppData/Local/Temp/cursor/screenshots/rules-builder-00-select-bot.png)

### What You Are Seeing

- `NEW GROUP`: Creates a folder/group for organizing bots.
- `NEW BOT`: Creates another bot record.
- Folder header row (`[DIR] ...`): Group container for related bots.
- `START ALL` / `STOP ALL`: Controls all bots in that folder.
- `DEL DIR`: Deletes the entire folder.
- Bot row controls:
  - Checkbox: marks bot for multi-select operations.
  - Play/Pause button: starts or stops that specific bot.
  - `[:]`: quick action menu for that bot.
- Bottom nav:
  - `BOTS`, `EDIT`, `MKT`, `P&L`, `LOG`, `DBG`, `VAR`, `CFG`.

---

## 2) Ruleset Builder Layout Overview

When you open `EDIT`, the builder is stacked in this order:

1. Bot identity and contract side controls.
2. Market assignment and auto-roll controls.
3. Trend configuration strip.
4. Rule toolbar (snapshots, sim, add-line buttons).
5. Rule list (each line is an editable logic/action record).
6. Strategy Assistant panel on desktop-wide layouts (hidden on narrow/mobile widths).

### Screenshot - Ruleset Builder Overview

![Ruleset builder overview](file:///C:/Users/pman/AppData/Local/Temp/cursor/screenshots/rules-builder-01-overview.png)

---

## 3) Header Row: Bot Identity, Side, Market, Auto-Roll

The top header contains the controls that affect how your rules execute against a market.

### 3.1 Bot Name

- Click the bot name text to edit inline.
- Press `Enter` or click away to save.
- If empty, it displays `UNTITLED BOT`.

### 3.2 Contract Side Toggle (`YES` / `NO`)

This sets the bot-level default contract side used by trade actions.

- `YES` active:
  - BUY means buy YES contracts.
  - SELL means sell YES contracts.
- `NO` active:
  - BUY means buy NO contracts.
  - SELL means sell NO contracts.

Important: This is not the same as LIMIT order direction. LIMIT has its own `BUY`/`SELL` action direction plus optional side override.

### 3.3 Market Ticker Chip

- Shows the assigned market ticker (example: `KXETH15M-...`).
- `[X]` inside this chip clears market assignment.

### 3.4 Auto-Roll Toggle

- Controls continuation to next contract in the same series.
- Shows `[ ]` when off, `[*]` when on.
- Uses inferred or stored series ticker (example: next `KXETH15M` contract).

### If No Market Is Assigned

The market area swaps to `MarketPickerTree`:

- Saved list tree (from Markets tab lists).
- Expand/collapse list nodes.
- Click ticker in a list to assign that market to the bot.
- `refresh` to pull latest saved lists.

---

## 4) Trend Configuration Strip

This row configures trend-derived variables used by your conditions.

- `WATCH` source:
  - `YES_price`, `NO_price`, `Bid`, `Ask`, `LastTraded`
- `EVERY` polling interval:
  - 500ms, 1s, 2s, 5s, 10s, 30s
- `CONFIRM AFTER ... IN A ROW`:
  - Integer input (minimum 1)
  - Defines strict streak length for trend confirmation

Output variables produced from this config include:

- `TrendUp`
- `TrendDown`

Behavior note:

- Duplicate quotes are ignored for strict up/down streak counting.

---

## 5) Rule Toolbar (Top of Rule List)

### Screenshot - Toolbar and Condition Rows

![Toolbar and first condition lines](file:///C:/Users/pman/AppData/Local/Temp/cursor/screenshots/rules-builder-03-with-rules.png)

The toolbar is split into two rows.

### 5.1 Utility Row

- `snapshots`: Opens snapshot modal to save/restore rulesets.
- `SIM`: Opens simulator workflow for rule execution testing.

### 5.2 Add-Line Row

Each button inserts one rule line at the bottom:

- `IF`: Start a condition chain.
- `AND`: Additional condition in the same chain.
- `OR`: Alternative condition in the same chain.
- `ELSE`: Action branch when chain result is false.
- `THEN`: Action branch when chain result is true.
- `GOTO`: Jump to line.
- `CONT`: Continue execution.
- `STOP`: Stop bot.
- `LOG`: Write log message.
- `NOOP`: No operation.
- `PAUSE`: Delay execution.
- `CX`: Cancel stale limits (`CANCEL_STALE`).
- `VAR`: Set variable (`SET_VAR`).
- `ALERT`: Raise alert text.

---

## 6) Rule Line Anatomy (Every Row in Rule List)

Every line includes:

- Drag handle: `::` (drag-and-drop reorder).
- Move up/down: `^` and `v`.
- Line number.
- Line type badge (`IF`, `AND`, `THEN`, etc).
- Editor area (condition builder or action builder).
- Optional execution counter (`xN`) when line has fired.
- Optional sim marker:
  - `V` = hit/executed in sim
  - `-` = skipped in sim
  - `>` = branched in sim
- Delete button: `[X]`.

### Drag-and-Drop Insert Between Lines

- Click and hold `::`.
- Drag to the target position.
- A green horizontal insertion indicator appears between lines.
- Drop to reorder.
- Reorder uses immediate persistence (`saveRulesImmediate`).

---

## 7) Condition Builder (IF / AND / OR Lines)

Condition rows use a three-part structure:

1. Left operand
2. Operator
3. Right operand

Each operand supports two modes:

- `variable`: choose from available variable groups
- `value`: enter numeric literal

### Variable/Value Toggle Behavior

- Toggling does not destroy line type.
- Clearing value input does not force-switch back to variable mode.
- Right side defaults to value mode if empty in many cases.

### Operators

Operator picker supports:

- `=`
- `!=`
- `>`
- `<`
- `>=`
- `<=`

---

## 8) Action Builder (THEN / ELSE and Standalone Action Lines)

Action content depends on action type.

### 8.1 Market Actions

- `BUY`: contracts at market.
- `SELL`: contracts at market.
- `CLOSE`: close open position.

### 8.2 LIMIT Action (Most Important)

LIMIT exposes:

- Direction: `BUY` or `SELL` (`order_action`).
- Optional side override: `BOT`, `YES`, `NO`.
  - `BOT`: use bot contract side toggle.
  - `YES`/`NO`: override only this action.
- Quantity field:
  - `value` literal or `var`.
- Price field:
  - `value` literal or `var`.
  - Optional signed cents offset (`+c` input).
  - Negative offset subtracts from variable value.

### Screenshot - LIMIT and Cancel Stale Examples

![Lower rules showing LIMIT and CXL STALE](file:///C:/Users/pman/AppData/Local/Temp/cursor/screenshots/rules-builder-04-lower-actions.png)

### 8.3 Flow and Utility Actions

- `GOTO`: jump line number (`value` or `var`).
- `CONTINUE`: continue flow.
- `STOP`: stop bot.
- `NOOP`: explicit do-nothing line.
- `PAUSE`: milliseconds delay (`value` or `var`).
- `CANCEL_STALE`: cancel resting limits older than `max_age_ms`.
- `SET_VAR`: set `var_name` to `value`.
- `LOG`: write message to log stream.
- `ALERT`: send alert text.

---

## 9) Snapshots Modal (Save, Restore, Built-Ins)

Use snapshots to preserve and reuse rule states.

### Screenshot - Snapshots Modal

![Snapshots modal with save/load/apply](file:///C:/Users/pman/AppData/Local/Temp/cursor/screenshots/rules-builder-05-snapshots-sidebar.png)

### Controls

- `SAVE SNAPSHOT`: stores current rules.
- `LOAD BUILT-IN STRATEGIES`: seeds predefined strategy snapshots.
- `THIS BOT`: snapshots created for current bot.
- `OTHER BOTS`: snapshots from different bots.
- `DEL`: remove snapshot.
- `APPLY`: restore snapshot to editor and close modal.
- `[X]`: close modal without applying.

---

## 10) Bulk Edit Banner (When Multiple Bots Selected)

When multiple bots are selected:

- Builder enters bulk template mode.
- Banner indicates selected bot count.
- `SAVE TO ALL N` pushes current editor rules to all selected bots.
- Strategy Assistant is disabled during bulk mode.

---

## 11) Strategy Assistant Panel (Desktop/Wide Layout)

On large screens, right-side assistant panel includes:

- Provider chips (Groq/Gemini/Mistral/OpenAI when configured).
- Message history.
- Instruction textarea.
- `SEND` button.
- `Refresh` provider/key state.
- `Clear` conversation history.
- Proposed rules section with:
  - `APPLY TO EDITOR`
  - `DISMISS`
- Collapse toggle (`[>]`) and collapsed vertical tab to reopen.

If no provider key is configured, send input is disabled and warning is shown.

---

## 12) Autosave and Persistence Behavior

- Most edits (line field changes, line add/delete/move arrows):
  - Debounced save (about 800ms).
- Drag-and-drop reordering:
  - Immediate save on drop.
- Snapshot apply:
  - Restores and refreshes rule set immediately.
- Trend config changes:
  - Saved via bot `PUT` as each field changes/blurs.

---

## 13) Variable Picker Groups (Condition and Action Inputs)

Variable dropdowns are loaded from `/api/bots/{id}/available-variables` and grouped for readability.

Common examples you will see:

- Price fields: `YES_price`, `NO_price`, `Bid`, `Ask`, `LastTraded`.
- Position state: `HasPosition`, `PositionSize`, `AbsPositionSize`.
- Lifecycle: `TimeToExpiry`, `RestingLimitCount`, `OldestRestingLimitAgeSec`.
- Trend outputs: `TrendUp`, `TrendDown`, `ConsecutiveUp`, `ConsecutiveDown`.

---

## 14) Practical Build Workflow (Recommended)

1. Set bot side (`YES` or `NO`) in header.
2. Confirm market assignment and auto-roll intent.
3. Configure trend source and cadence.
4. Add condition chain:
   - Start with `IF`
   - Extend with `AND`/`OR`
5. Add `THEN`/`ELSE` actions.
6. Add safety lines:
   - position guard
   - resting limit guard
   - time-to-expiry window
   - optional `CANCEL_STALE`
7. Use `SIM` before live operation.
8. Save named snapshot once stable.
9. Reorder with drag-and-drop and re-simulate after structural changes.

---

## 15) Troubleshooting Checklist

- Rule not firing:
  - Verify condition chain logic (`IF` + `AND`/`OR`).
  - Check variable names and literal/value mode.
  - Confirm market is assigned.
- Wrong LIMIT behavior:
  - Confirm LIMIT direction (`BUY`/`SELL`) and side override (`BOT`/`YES`/`NO`).
  - Validate price source and cents offset sign.
- Duplicate attempts:
  - Add/verify `RestingLimitCount` guard.
  - Add/verify position-size guard.
  - Add `CANCEL_STALE` policy.
- No assistant response:
  - Set provider API key in `CFG`.
  - Confirm provider selected and key state refreshed.

---

## 16) Quick Reference of Line Types

- Conditions: `IF`, `AND`, `OR`
- Branches: `THEN`, `ELSE`
- Trade: `BUY`, `SELL`, `LIMIT`, `CLOSE`
- Flow: `GOTO`, `CONTINUE`, `STOP`, `PAUSE`, `NOOP`
- Maintenance: `CANCEL_STALE`, `SET_VAR`, `LOG`, `ALERT`

---

If you want, I can also generate a second version of this guide as a "one-screen cheat sheet" with compact action recipes (entry, take-profit, stale-cancel, and time-window templates).
