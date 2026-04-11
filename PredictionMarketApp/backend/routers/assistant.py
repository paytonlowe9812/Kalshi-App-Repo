import json
import logging
import re
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models import RuleLine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class StrategyChatMessage(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str


class StrategyChatRequest(BaseModel):
    bot_id: int
    messages: list[StrategyChatMessage]


class StrategyChatResponse(BaseModel):
    reply: str
    suggested_rules: Optional[list[dict[str, Any]]] = None
    rules_error: Optional[str] = None


def _settings_map() -> dict[str, str]:
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] or "" for row in rows}


def _strategy_system_prompt(bot: dict, rules: list[dict]) -> str:
    rules_json = json.dumps(rules, indent=2)
    return f"""You are a strategy assistant for Kalshi Bot Builder.
Help users design and edit bot rules in plain language. Be concise; prefer actionable rule lines.

## Rule line JSON (array order = execution order)
Each object fields:
- line_number: integer (1-based; you may omit, server renumbers)
- line_type: IF | AND | OR | THEN | ELSE | GOTO | CONTINUE | STOP | NOOP | PAUSE | LOG | ALERT
- For IF/AND/OR: left_operand (variable name or numeric string), operator: eq | neq | gt | lt | gte | lte, right_operand
- For THEN/ELSE: action_type: BUY | SELL | LIMIT | CLOSE | SET_VAR | STOP | NOOP | PAUSE | LOG | ALERT | CANCEL_STALE
- action_params: JSON **string** (e.g. "{{}}", "{{\\"contracts\\":1}}", "{{\\"contracts\\":1,\\"price\\":50,\\"side\\":\\"yes\\"}}" for LIMIT; price in cents 1-99)
- group_id, group_logic: optional strings for grouping

## Useful variables
PositionSize, AbsPositionSize, HasPosition, RestingLimitCount, OldestRestingLimitAgeSec, YES_price, NO_price, Bid, Ask, LastTraded, TimeToExpiry, DistanceFromStrike, DailyPnL, FillPrice; user vars from SET_VAR.

## Tips
- Resting limits do not change PositionSize until fill; use RestingLimitCount to avoid duplicate limits.
- Bot default contract side is below; LIMIT can set side yes|no in action_params.

## Current bot
- name: {bot.get("name") or ""}
- market_ticker: {bot.get("market_ticker") or ""}
- contract_side: {bot.get("contract_side") or "yes"}
- auto_roll: {bool(bot.get("auto_roll"))}

## Current rules
```json
{rules_json}
```

## When you output a full replacement rule set
End with exactly one fenced block:

```strategy_rules
[ ... JSON array of rule objects ... ]
```

If you are only explaining or answering without changing rules, do NOT include a strategy_rules block.
"""


def _strip_strategy_block(text: str) -> tuple[str, Optional[str]]:
    """Return (display_text, raw_json_inside_block or None)."""
    m = re.search(r"```strategy_rules\s*([\s\S]*?)```", text, re.IGNORECASE)
    if not m:
        return text.strip(), None
    inner = m.group(1).strip()
    display = (text[: m.start()] + text[m.end() :]).strip()
    return display, inner


def _parse_and_validate_rules(raw_json: str) -> tuple[Optional[list[dict]], Optional[str]]:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in strategy_rules block: {e}"
    if not isinstance(data, list):
        return None, "strategy_rules must be a JSON array"
    normalized: list[dict] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            return None, f"Rule at index {i} is not an object"
        ap = item.get("action_params")
        if ap is not None and not isinstance(ap, str):
            try:
                ap = json.dumps(ap)
            except (TypeError, ValueError):
                ap = "{}"
        d = {
            "line_number": i + 1,
            "line_type": str(item.get("line_type", "NOOP")),
            "left_operand": item.get("left_operand"),
            "operator": item.get("operator"),
            "right_operand": item.get("right_operand"),
            "action_type": item.get("action_type"),
            "action_params": ap,
            "group_id": item.get("group_id"),
            "group_logic": item.get("group_logic"),
        }
        try:
            RuleLine(**d)
        except Exception as e:
            return None, f"Line {i + 1} invalid: {e}"
        normalized.append(d)
    return normalized, None


async def _openai_complete(api_key: str, model: str, system: str, messages: list[dict]) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = (e.response.text or "")[:500]
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI error {e.response.status_code}: {body}",
            ) from e
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as e:
            raise HTTPException(502, "Unexpected OpenAI response shape") from e


async def _anthropic_complete(api_key: str, model: str, system: str, messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 8192,
                "system": system,
                "messages": messages,
            },
        )
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = (e.response.text or "")[:500]
            raise HTTPException(
                status_code=502,
                detail=f"Anthropic error {e.response.status_code}: {body}",
            ) from e
        data = r.json()
        try:
            parts = data.get("content") or []
            return "".join(p.get("text", "") for p in parts if p.get("type") == "text")
        except Exception as e:
            raise HTTPException(502, "Unexpected Anthropic response shape") from e


@router.post("/strategy-chat", response_model=StrategyChatResponse)
async def strategy_chat(data: StrategyChatRequest):
    s = _settings_map()
    api_key = (s.get("strategy_llm_api_key") or "").strip()
    if not api_key:
        raise HTTPException(
            400,
            "No strategy LLM API key configured. Add it under CONFIG (Strategy assistant).",
        )
    provider = (s.get("strategy_llm_provider") or "openai").strip().lower()
    if provider not in ("openai", "anthropic"):
        provider = "openai"
    default_model = "gpt-4o-mini" if provider == "openai" else "claude-3-5-sonnet-20241022"
    model = (s.get("strategy_llm_model") or "").strip() or default_model

    db = get_db()
    bot = db.execute("SELECT * FROM bots WHERE id = ?", (data.bot_id,)).fetchone()
    if not bot:
        raise HTTPException(404, "Bot not found")
    bot_d = dict(bot)
    rows = db.execute(
        "SELECT * FROM rules WHERE bot_id = ? ORDER BY line_number",
        (data.bot_id,),
    ).fetchall()
    rules = [dict(r) for r in rows]

    system = _strategy_system_prompt(bot_d, rules)

    chat_messages: list[dict] = []
    for m in data.messages:
        role = (m.role or "").lower()
        if role not in ("user", "assistant"):
            raise HTTPException(400, f"Invalid message role: {m.role}")
        chat_messages.append({"role": role, "content": m.content})

    if not chat_messages or chat_messages[-1]["role"] != "user":
        raise HTTPException(400, "Last message must be from user")

    try:
        if provider == "openai":
            raw = await _openai_complete(api_key, model, system, chat_messages)
        else:
            raw = await _anthropic_complete(api_key, model, system, chat_messages)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("LLM call failed")
        raise HTTPException(502, f"LLM request failed: {e}") from e

    display, block = _strip_strategy_block(raw)
    suggested: Optional[list[dict]] = None
    rules_error: Optional[str] = None
    if block:
        suggested, rules_error = _parse_and_validate_rules(block)
        if rules_error:
            suggested = None

    return StrategyChatResponse(
        reply=display or raw.strip(),
        suggested_rules=suggested,
        rules_error=rules_error,
    )
