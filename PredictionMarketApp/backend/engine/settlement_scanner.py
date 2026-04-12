"""
Settlement scanner — detects when a Kalshi binary contract settles and
back-fills exit_price + pnl on any open trade_log rows for that market.

Kalshi 15-min contracts settle automatically (no SELL action from the bot).
Without this scanner, every BUY entry would show P&L = NULL forever.

Settlement logic:
  result = "yes"  →  YES settles at 100¢,  NO settles at 0¢
  result = "no"   →  YES settles at 0¢,    NO settles at 100¢

P&L = (settlement_price - entry_price) / 100 * contracts
"""
import logging
from backend.database import get_db
from backend.kalshi.client import get_kalshi_client

logger = logging.getLogger(__name__)


async def scan_and_settle() -> int:
    """
    Check all open (un-exited) trade_log BUY/LIMIT entries against the
    Kalshi market status.  Back-fill exit_price and pnl when settled.
    Returns the number of rows updated.
    """
    client = get_kalshi_client()
    if not client:
        return 0

    db = get_db()

    # All entries that look like an open long — no exit yet.
    open_entries = db.execute("""
        SELECT t.id, t.bot_id, t.market_ticker, t.action,
               t.entry_price, t.contracts,
               COALESCE(b.contract_side, 'yes') AS contract_side
        FROM   trade_log t
        LEFT JOIN bots b ON t.bot_id = b.id
        WHERE  t.action IN ('BUY', 'LIMIT_YES', 'LIMIT_NO')
          AND  t.exit_price IS NULL
          AND  t.market_ticker IS NOT NULL
    """).fetchall()

    if not open_entries:
        return 0

    # Group by ticker to minimise API calls.
    by_ticker: dict[str, list] = {}
    for row in open_entries:
        tkr = row["market_ticker"]
        by_ticker.setdefault(tkr, []).append(row)

    updated = 0
    for ticker, entries in by_ticker.items():
        try:
            mdata = await client.get_market(ticker)
            market = mdata.get("market", mdata)
            status = (market.get("status") or "").lower()
            result = (market.get("result") or "").lower()   # "yes" | "no" | ""

            if status not in ("settled", "determined", "finalized", "closed"):
                continue
            if result not in ("yes", "no"):
                # Market closed but result unknown yet — skip until it appears.
                continue

            for entry in entries:
                action = entry["action"]
                contract_side = (entry["contract_side"] or "yes").lower()

                # Determine the side that was actually bought.
                if action == "LIMIT_YES":
                    side = "yes"
                elif action == "LIMIT_NO":
                    side = "no"
                else:
                    # BUY — inherit the bot's contract_side.
                    side = contract_side

                # Binary settlement: winning side pays out 100¢.
                if result == "yes":
                    settlement_price = 100.0 if side == "yes" else 0.0
                else:
                    settlement_price = 100.0 if side == "no" else 0.0

                entry_p  = float(entry["entry_price"] or 0)
                contracts = int(entry["contracts"] or 1)
                pnl = round((settlement_price - entry_p) / 100.0 * contracts, 4)

                db.execute(
                    "UPDATE trade_log SET exit_price = ?, pnl = ? WHERE id = ?",
                    (settlement_price, pnl, entry["id"]),
                )
                updated += 1
                logger.info(
                    "Settlement: trade_log id=%s  ticker=%s  side=%s  result=%s  "
                    "entry=%.1f  settle=%.0f  pnl=%.4f",
                    entry["id"], ticker, side, result,
                    entry_p, settlement_price, pnl,
                )

            if updated:
                db.commit()

        except Exception as e:
            logger.error("Settlement scan error for %s: %s", ticker, e)

    return updated
