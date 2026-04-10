import sqlite3
import os
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "app.db"


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


_conn: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = get_connection()
    return _conn


MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS api_keys (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL,
        key_id     TEXT NOT NULL,
        key_secret TEXT NOT NULL,
        is_active  INTEGER DEFAULT 0,
        is_demo    INTEGER DEFAULT 0,
        last_used  TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS groups (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL,
        parent_id  INTEGER REFERENCES groups(id),
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS bots (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        group_id        INTEGER REFERENCES groups(id),
        market_ticker   TEXT,
        trigger_type    TEXT DEFAULT 'loop',
        trigger_value   TEXT,
        trigger_time    TEXT,
        status          TEXT DEFAULT 'stopped',
        is_paper        INTEGER DEFAULT 1,
        error_message   TEXT,
        last_run_at     TEXT,
        run_count       INTEGER DEFAULT 0,
        sort_order      INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS rules (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id        INTEGER NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
        line_number   INTEGER NOT NULL,
        line_type     TEXT NOT NULL,
        left_operand  TEXT,
        operator      TEXT,
        right_operand TEXT,
        action_type   TEXT,
        action_params TEXT,
        group_id      TEXT,
        group_logic   TEXT,
        exec_count    INTEGER DEFAULT 0,
        UNIQUE(bot_id, line_number)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS snapshots (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id     INTEGER NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
        name       TEXT,
        rules_json TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS variables (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id  INTEGER NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
        name    TEXT NOT NULL,
        value   TEXT DEFAULT '0',
        UNIQUE(bot_id, name)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS sentiment_indexes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL UNIQUE,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS sentiment_index_markets (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        index_id   INTEGER NOT NULL REFERENCES sentiment_indexes(id) ON DELETE CASCADE,
        ticker     TEXT NOT NULL,
        label      TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS trade_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id          INTEGER REFERENCES bots(id),
        bot_name        TEXT,
        market_ticker   TEXT,
        market_title    TEXT,
        action          TEXT,
        contracts       INTEGER,
        entry_price     REAL,
        exit_price      REAL,
        pnl             REAL,
        rule_line       INTEGER,
        is_paper        INTEGER DEFAULT 1,
        kalshi_order_id TEXT,
        logged_at       TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS trading_schedule (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        day_of_week INTEGER NOT NULL,
        is_enabled  INTEGER DEFAULT 1,
        start_time  TEXT NOT NULL,
        end_time    TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS favorites (
        ticker   TEXT PRIMARY KEY,
        added_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS market_lists (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS market_list_items (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        list_id    INTEGER NOT NULL REFERENCES market_lists(id) ON DELETE CASCADE,
        ticker     TEXT NOT NULL,
        title      TEXT,
        sort_order INTEGER DEFAULT 0,
        UNIQUE(list_id, ticker)
    );
    """,
]

COLUMN_MIGRATIONS = [
    ("bots", "auto_roll", "INTEGER DEFAULT 0"),
    ("bots", "series_ticker", "TEXT"),
    ("bots", "roll_count", "INTEGER DEFAULT 0"),
    ("bots", "last_roll_at", "TEXT"),
    ("bots", "contract_side", "TEXT DEFAULT 'yes'"),
    ("sentiment_index_markets", "series_ticker", "TEXT"),
    ("sentiment_index_markets", "auto_roll", "INTEGER DEFAULT 1"),
]

DEFAULT_SETTINGS = {
    "theme": "dark",
    "loop_interval_ms": "500",
    "max_simultaneous_bots": "10",
    "paper_trading_mode": "true",
    "daily_loss_limit_enabled": "false",
    "daily_loss_limit_amount": "100",
    "max_open_positions": "10",
    "max_open_positions_enabled": "false",
    "window_exposure_cap_enabled": "false",
    "window_exposure_cap_contracts": "30",
    "circuit_breaker_enabled": "false",
    "circuit_breaker_force_close": "false",
    "trading_schedule_enabled": "false",
    "license_key": "",
    "license_valid": "false",
    "first_launch": "true",
}


def init_db():
    conn = get_db()
    for sql in MIGRATIONS:
        conn.executescript(sql)

    for table, col, col_type in COLUMN_MIGRATIONS:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    for key, value in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    group_exists = conn.execute(
        "SELECT COUNT(*) FROM groups WHERE name = 'Examples'"
    ).fetchone()[0]
    if not group_exists:
        conn.execute("INSERT INTO groups (name, sort_order) VALUES ('Examples', 0)")
        group_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO bots (name, group_id, status, is_paper) VALUES (?, ?, 'stopped', 1)",
            ("Daily Loss Limit Example", group_id),
        )
        bot_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO rules (bot_id, line_number, line_type, left_operand, operator, right_operand) "
            "VALUES (?, 1, 'IF', 'DailyPnL', 'lt', '-10')",
            (bot_id,),
        )
        conn.execute(
            "INSERT INTO rules (bot_id, line_number, line_type, action_type) "
            "VALUES (?, 2, 'THEN', 'STOP')",
            (bot_id,),
        )

    conn.commit()
