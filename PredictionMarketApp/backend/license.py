import httpx
from datetime import datetime, timedelta
from backend.database import get_db

GUMROAD_API = "https://api.gumroad.com/v2/licenses/verify"
PRODUCT_ID = "TBD"
LICENSE_CHECK_INTERVAL_DAYS = 7


async def validate_license(key: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GUMROAD_API,
                data={
                    "product_id": PRODUCT_ID,
                    "license_key": key,
                    "increment_uses_count": False,
                },
            )
        data = resp.json()
        valid = data.get("success", False)
        if valid:
            db = get_db()
            db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('license_key', ?)",
                (key,),
            )
            db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('license_valid', 'true')"
            )
            db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('license_checked_at', ?)",
                (datetime.utcnow().isoformat(),),
            )
            db.commit()
        return {"valid": valid, "message": data.get("message", "")}
    except Exception as e:
        return {"valid": False, "message": str(e)}


def get_license_status() -> dict:
    db = get_db()
    valid_row = db.execute(
        "SELECT value FROM settings WHERE key = 'license_valid'"
    ).fetchone()
    valid = valid_row and valid_row[0] == "true"

    paper_row = db.execute(
        "SELECT value FROM settings WHERE key = 'paper_trading_mode'"
    ).fetchone()
    paper = paper_row and paper_row[0] == "true"

    mode = "paper" if (paper or not valid) else "live"
    return {"valid": valid, "mode": mode}


def should_revalidate() -> bool:
    db = get_db()
    row = db.execute(
        "SELECT value FROM settings WHERE key = 'license_checked_at'"
    ).fetchone()
    if not row or not row[0]:
        return True
    try:
        checked = datetime.fromisoformat(row[0])
        return datetime.utcnow() - checked > timedelta(days=LICENSE_CHECK_INTERVAL_DAYS)
    except ValueError:
        return True
