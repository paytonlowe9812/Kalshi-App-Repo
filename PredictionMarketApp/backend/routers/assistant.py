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

_PROVIDER_KEYS = {
    "openai": "strategy_llm_api_key",
    "groq": "strategy_llm_groq_key",
    "gemini": "strategy_llm_gemini_key",
    "mistral": "strategy_llm_mistral_key",
}

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.0-flash",
    "mistral": "mistral-small-latest",
}

_MODEL_SETTINGS_KEYS = {
    "openai": "strategy_llm_model",
    "groq": "strategy_llm_groq_model",
    "gemini": "strategy_llm_gemini_model",
    "mistral": "strategy_llm_mistral_model",
}


class _RateLimitError(Exception):
    pass


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
    provider_used: Optional[str] = None


class SaveHistoryRequest(BaseModel):
    messages: list[StrategyChatMessage]


def _settings_map() -> dict[str, str]:
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] or "" for row in rows}


# Settings > Strategy Assistant: optional extra text is appended AFTER this built-in prefix
# (never replaced). The server then appends "## Current bot", rules JSON, and strategy_rules rules.
_DEFAULT_STRATEGY_SYSTEM_PREFIX = """You are a strategy assistant for Kalshi Bot Builder.
Help users design and edit bot rules in plain language. Be concise; prefer actionable rule lines.

## Rule line JSON (array order = execution order)
Each object fields:
- line_number: integer (1-based; you may omit, server renumbers)
- line_type: IF | AND | OR | THEN | ELSE | GOTO | CONTINUE | STOP | NOOP | PAUSE | LOG | ALERT
- For IF/AND/OR: left_operand (variable name or numeric string), operator: eq | neq | gt | lt | gte | lte, right_operand (variable name OR plain numeric string — NO expressions, NO formulas, e.g. "20" not "NO_price*0.2")
- For THEN/ELSE: action_type: BUY | SELL | LIMIT | CLOSE | SET_VAR | STOP | NOOP | PAUSE | LOG | ALERT | CANCEL_STALE
- action_params: always a JSON **string** (serialize the object, then put that string in the rule's action_params field). Use double quotes inside the JSON.
- LIMIT action_params object: include "order_action":"buy"|"sell", optional "side":"yes"|"no" (contract side override; omit to use the bot default side), and "contracts" (int) or "contracts_var" (string). For limit **price** in cents (1-99): either (a) "price": <int> for a fixed cent price, or (b) "price_var": "<VariableName>" for a dynamic base price from the engine (LastTraded, Bid, Ask, YES_price, NO_price, FillPrice, etc.) plus optional "price_offset": <signed int> — **offset is added in cents after** the variable resolves (e.g. price_offset 5 = five cents above that value; -5 = five below). When using price_var, omit "price". Example JSON before stringifying: {"order_action":"buy","contracts":1,"price_var":"LastTraded","price_offset":5}
- group_id, group_logic: optional strings for grouping

## Useful variables
PositionSize, AbsPositionSize, HasPosition, RestingLimitCount, OldestRestingLimitAgeSec, YES_price, NO_price, Bid, Ask, LastTraded, TimeToExpiry, DistanceFromStrike, DailyPnL, FillPrice; user vars from SET_VAR.

## Trend variables (auto-computed, configurable per bot)
- ConsecutiveUp   — how many consecutive price samples strictly increased
- ConsecutiveDown — how many consecutive price samples strictly decreased
- TrendUp         — 1 if ConsecutiveUp  >= confirm_count, else 0
- TrendDown       — 1 if ConsecutiveDown >= confirm_count, else 0

## Critical safety rules — ALWAYS follow these or the bot will spam infinite orders
1. Every BUY / SELL / LIMIT action block MUST be preceded by a position/order guard.
   - For market orders: add `IF HasPosition eq 0` before buying,
     and `IF HasPosition eq 1` (or `IF PositionSize gt 0`) before selling.
   - For limit orders: ALWAYS add `IF RestingLimitCount eq 0` before placing a LIMIT.
     Without this guard the bot places a new limit order every loop tick — infinite spam.
   - Combine guards with AND lines when multiple conditions are needed.
2. Never emit a LIMIT or BUY/SELL without at least one guard that becomes false once the
   order/position exists — otherwise the action fires every loop tick indefinitely.
3. When building a buy-low / sell-high strategy, the typical safe skeleton is:
   ```
   IF  HasPosition    eq  0        ← no open position yet
   AND YES_price      lt  <entry>  ← price condition
   THEN BUY ...

   IF  HasPosition    eq  1        ← already in position
   AND YES_price      gt  <exit>   ← exit condition
   THEN SELL ...
   ```
   For limit orders replace HasPosition guard with RestingLimitCount eq 0.

## Common sense guards — always apply these unless the user explicitly says otherwise
- **Loss limit**: add a stop-loss — if DailyPnL drops below a reasonable threshold (e.g. -5), STOP the bot.
- **Expiry guard**: if the strategy depends on price movement, add `IF TimeToExpiry gt 5` (or similar) to avoid trading in the last few minutes before settlement where prices can be erratic.
- **Position cap**: use `IF AbsPositionSize lt <max>` (e.g. 5) before BUY/SELL to prevent runaway position size.
- **No double entry**: always check `HasPosition eq 0` before any BUY and `HasPosition eq 1` before any SELL — never omit these even if the user doesn't ask for them.
- **No stale limits**: if placing limit orders, consider adding a CANCEL_STALE action with a reasonable max_age_ms (e.g. 30000 = 30 seconds) so old unfilled limits don't accumulate.
- **Sensible price bounds**: for LIMIT orders, keep price between 2 and 98 cents — avoid 1 or 99 as Kalshi may reject them.
- **Small default size**: default to 1 contract unless the user specifies more — never generate strategies with large contract counts without being asked.

## Tips
- Resting limits do not change PositionSize until fill; use RestingLimitCount to avoid duplicate limits.
- Bot default contract side is below; LIMIT may override side with side yes|no, and direction is controlled by order_action buy|sell.
- If the user asks for a limit at "variable plus/minus N cents", emit LIMIT with price_var + price_offset (not a formula in operands). E.g. five cents under last trade: price_var LastTraded, price_offset -5. Five cents over Bid: price_var Bid, price_offset 5.

"""


def _strategy_system_suffix(bot: dict, rules: list[dict]) -> str:
    rules_json = json.dumps(rules, indent=2)
    return f"""## Current bot
- name: {bot.get("name") or ""}
- market_ticker: {bot.get("market_ticker") or ""}
- contract_side: {bot.get("contract_side") or "yes"}
- auto_roll: {bool(bot.get("auto_roll"))}
- trend_price_source: {bot.get("trend_price_source") or "YES_price"} (which price ConsecutiveUp/Down tracks)
- trend_poll_ms: {bot.get("trend_poll_ms") or 1000} (ms between trend samples)
- trend_confirm_count: {bot.get("trend_confirm_count") or 3} (samples needed for TrendUp/TrendDown = 1)

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


def _strategy_system_prompt(bot: dict, rules: list[dict], settings: dict[str, str]) -> str:
    extra = (settings.get("strategy_llm_system_prompt") or "").strip()
    core = _DEFAULT_STRATEGY_SYSTEM_PREFIX.rstrip()
    if extra:
        core = core + "\n\n" + extra
    return core + "\n\n" + _strategy_system_suffix(bot, rules)


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


# ── Provider implementations ──────────────────────────────────────────────────

async def _openai_complete(api_key: str, model: str, system: str, messages: list[dict]) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise _RateLimitError("OpenAI rate limited")
            body = (e.response.text or "")[:500]
            raise HTTPException(502, f"OpenAI error {e.response.status_code}: {body}") from e
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as e:
            raise HTTPException(502, "Unexpected OpenAI response shape") from e


async def _groq_complete(api_key: str, model: str, system: str, messages: list[dict]) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise _RateLimitError("Groq rate limited")
            body = (e.response.text or "")[:500]
            raise HTTPException(502, f"Groq error {e.response.status_code}: {body}") from e
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as e:
            raise HTTPException(502, "Unexpected Groq response shape") from e


async def _gemini_complete(api_key: str, model: str, system: str, messages: list[dict]) -> str:
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.3},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, json=payload)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise _RateLimitError("Gemini rate limited")
            body = (e.response.text or "")[:500]
            raise HTTPException(502, f"Gemini error {e.response.status_code}: {body}") from e
        data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"] or ""
        except (KeyError, IndexError) as e:
            raise HTTPException(502, "Unexpected Gemini response shape") from e


async def _mistral_complete(api_key: str, model: str, system: str, messages: list[dict]) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise _RateLimitError("Mistral rate limited")
            body = (e.response.text or "")[:500]
            raise HTTPException(502, f"Mistral error {e.response.status_code}: {body}") from e
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as e:
            raise HTTPException(502, "Unexpected Mistral response shape") from e


_COMPLETERS = {
    "openai": _openai_complete,
    "groq": _groq_complete,
    "gemini": _gemini_complete,
    "mistral": _mistral_complete,
}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/history/{bot_id}")
def get_history(bot_id: int):
    db = get_db()
    rows = db.execute(
        "SELECT role, content FROM ai_chat_history WHERE bot_id = ? ORDER BY id",
        (bot_id,),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


@router.post("/history/{bot_id}")
def save_history(bot_id: int, data: SaveHistoryRequest):
    db = get_db()
    for msg in data.messages:
        db.execute(
            "INSERT INTO ai_chat_history (bot_id, role, content) VALUES (?, ?, ?)",
            (bot_id, msg.role, msg.content),
        )
    db.commit()
    return {"status": "ok"}


@router.delete("/history/{bot_id}")
def clear_history(bot_id: int):
    db = get_db()
    db.execute("DELETE FROM ai_chat_history WHERE bot_id = ?", (bot_id,))
    db.commit()
    return {"status": "ok"}


@router.post("/strategy-chat", response_model=StrategyChatResponse)
async def strategy_chat(data: StrategyChatRequest):
    s = _settings_map()

    active_provider = (s.get("strategy_llm_provider") or "groq").strip().lower()
    if active_provider not in _COMPLETERS:
        active_provider = "groq"

    active_key = (s.get(_PROVIDER_KEYS[active_provider]) or "").strip()
    if not active_key:
        raise HTTPException(
            400,
            f"No API key configured for '{active_provider}'. Switch providers or add a key under CONFIG.",
        )
    priority = [active_provider]

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

    system = _strategy_system_prompt(bot_d, rules, s)

    chat_messages: list[dict] = []
    for m in data.messages:
        role = (m.role or "").lower()
        if role not in ("user", "assistant"):
            raise HTTPException(400, f"Invalid message role: {m.role}")
        chat_messages.append({"role": role, "content": m.content})

    if not chat_messages or chat_messages[-1]["role"] != "user":
        raise HTTPException(400, "Last message must be from user")

    raw: str = ""
    provider_used: str = ""
    last_exc: Exception | None = None

    for provider_name in priority:
        key = (s.get(_PROVIDER_KEYS[provider_name]) or "").strip()
        if not key:
            continue
        model_key = _MODEL_SETTINGS_KEYS.get(provider_name, "strategy_llm_model")
        model = (s.get(model_key) or "").strip() or _DEFAULT_MODELS[provider_name]
        completer = _COMPLETERS[provider_name]
        try:
            raw = await completer(key, model, system, chat_messages)
            provider_used = provider_name
            break
        except _RateLimitError as e:
            logger.warning("Rate limited on %s, trying fallback: %s", provider_name, e)
            last_exc = e
            continue
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("LLM call failed for provider %s", provider_name)
            last_exc = e
            break

    if not provider_used:
        detail = str(last_exc) if last_exc else "All configured providers rate-limited or unavailable"
        raise HTTPException(502, detail)

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
        provider_used=provider_used,
    )
