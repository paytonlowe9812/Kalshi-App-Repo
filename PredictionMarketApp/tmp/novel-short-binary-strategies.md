# Novel Short-Binary Strategy Guide

This note describes the three injected snapshot strategies:

- `Strategy: Drift ladder maker (seed)`
- `Strategy: Exhaustion snapback maker (seed)`
- `Strategy: Late squeeze clip (seed)`

All three are designed for short-horizon binary markets with these shared constraints:

- limit-only entries and exits (`LIMIT` with `order_action`)
- max one open contract (`HasPosition == 0` and `AbsPositionSize < 1`)
- no duplicate resting orders (`RestingLimitCount == 0` before entry)
- stale order cleanup (`CANCEL_STALE` after 30 seconds)
- hard loss cutoff (`STOP` when `DailyPnL < -4`)

## 1) Drift ladder maker

### Core idea
Ride early-to-mid window directional drift, enter passively just below the touch, and scale out with limit sells when momentum weakens or expiry approaches.

### Entry profile
- Requires `TrendUp == 1`
- Requires `ConsecutiveUp` between `2` and `6`
- Requires `TimeToExpiry` between `7` and `13`
- Requires `LastTraded` between `32` and `78`
- Entry order: `LIMIT buy` at `Bid - 1`

### Exit profile
- If `Bid > FillPrice`: place `LIMIT sell` at `Bid`
- If `TrendDown == 1`: place `LIMIT sell` at `Bid - 1`
- If `TimeToExpiry < 2`: place `LIMIT sell` at `Bid - 2`

### Where it should perform best
- Persistent directional sessions with shallow pullbacks
- Moderate-volatility intervals where spread is stable

### Main failure mode
- Choppy range action after entry (fills happen but follow-through fails)

## 2) Exhaustion snapback maker

### Core idea
Buy washed-out short-term drops, then exit on rebound/normalization using maker limits.

### Entry profile
- Requires `TrendDown == 1`
- Requires `ConsecutiveDown >= 3`
- Requires `TimeToExpiry` between `8` and `14`
- Requires `LastTraded` between `14` and `42`
- Entry order: `LIMIT buy` at `Bid - 2`

### Exit profile
- If reversal confirms (`TrendUp == 1` and `LastTraded > FillPrice`): `LIMIT sell` at `Ask - 1`
- If rebound extends (`LastTraded > 49`): `LIMIT sell` at `Bid`
- If downtrend persists (`ConsecutiveDown >= 5`): defensive `LIMIT sell` at `Bid - 2`
- If `TimeToExpiry < 2`: defensive `LIMIT sell` at `Bid - 2`

### Where it should perform best
- Mean-reverting bursts after abrupt downside sweeps
- Sessions with temporary liquidity gaps that revert

### Main failure mode
- True trend days where downside persists and bounce never forms

## 3) Late squeeze clip

### Core idea
Capture late-session continuation squeezes with very tight risk windows and aggressive timed exits.

### Entry profile
- Requires `TrendUp == 1`
- Requires `ConsecutiveUp >= 2`
- Requires `TimeToExpiry` between `4` and `9`
- Requires `Bid` between `58` and `90`
- Entry order: `LIMIT buy` at `Bid - 1`

### Exit profile
- If `Bid > FillPrice`: `LIMIT sell` at `Ask - 2`
- If squeeze extends (`Bid > 84`): `LIMIT sell` at `Bid`
- If momentum breaks (`TrendDown == 1`): `LIMIT sell` at `Bid - 2`
- If `TimeToExpiry < 1`: forced `LIMIT sell` at `Bid - 3`

### Where it should perform best
- Strong late-cycle continuation bursts
- Fast tape with directional urgency into close

### Main failure mode
- Late fakeouts: price spikes then immediately mean-reverts

## Practical operating notes

- Strategies do not hardcode `side`, so they use each bot's `contract_side`.
- For `NO` bots, your variable layer already flips bid/ask/last-traded context to the active side.
- These are edge templates, not guarantees. Use small size and compare live fill quality before scaling.
