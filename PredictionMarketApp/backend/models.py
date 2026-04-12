from pydantic import BaseModel
from typing import Any, Optional


class SettingUpdate(BaseModel):
    key: str
    value: str


class SettingsBulkUpdate(BaseModel):
    # Values may be JSON bool/number from clients; settings router coerces to strings for SQLite.
    settings: dict[str, Any]


class ApiKeyCreate(BaseModel):
    name: str
    key_id: str
    key_secret: str


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class GroupCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class BotCreate(BaseModel):
    name: str
    group_id: Optional[int] = None
    market_ticker: Optional[str] = None
    trigger_type: str = "loop"
    trigger_value: Optional[str] = None
    trigger_time: Optional[str] = None
    auto_roll: bool = False
    series_ticker: Optional[str] = None
    contract_side: Optional[str] = "yes"


class BotUpdate(BaseModel):
    name: Optional[str] = None
    group_id: Optional[int] = None
    market_ticker: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    trigger_time: Optional[str] = None
    auto_roll: Optional[bool] = None
    series_ticker: Optional[str] = None
    contract_side: Optional[str] = None
    trend_poll_ms: Optional[int] = None
    trend_confirm_count: Optional[int] = None
    trend_price_source: Optional[str] = None


class BotMove(BaseModel):
    group_id: Optional[int] = None


class RuleLine(BaseModel):
    line_number: int
    line_type: str
    left_operand: Optional[str] = None
    operator: Optional[str] = None
    right_operand: Optional[str] = None
    action_type: Optional[str] = None
    action_params: Optional[str] = None
    group_id: Optional[str] = None
    group_logic: Optional[str] = None


class RuleSetUpdate(BaseModel):
    rules: list[RuleLine]


class SnapshotCreate(BaseModel):
    name: Optional[str] = None


class IndexCreate(BaseModel):
    name: str
    markets: list[dict]


class IndexUpdate(BaseModel):
    name: Optional[str] = None
    markets: Optional[list[dict]] = None


class MarketListCreate(BaseModel):
    name: str


class MarketListUpdate(BaseModel):
    name: Optional[str] = None


class MarketListItemAdd(BaseModel):
    ticker: str
    title: Optional[str] = None


class SimulationRequest(BaseModel):
    bot_id: int
    variable_overrides: dict[str, float] = {}


class SimulationStep(BaseModel):
    line_number: int
    result: str
    reason: str = ""
    action_fired: Optional[dict] = None
    goto_line: Optional[int] = None


class SimulationResponse(BaseModel):
    steps: list[SimulationStep]
    final_action: Optional[dict] = None
    variables_after: dict[str, float] = {}


class LicenseValidate(BaseModel):
    key: str


class VariableUpdate(BaseModel):
    variables: dict[str, str]


class BulkBotEdit(BaseModel):
    trigger_type: Optional[str] = None
    market_ticker: Optional[str] = None


class Action(BaseModel):
    type: str
    contracts: Optional[int] = None
    contracts_var: Optional[str] = None
    price: Optional[float] = None
    price_var: Optional[str] = None
    # LIMIT: added to resolved limit price (cents), e.g. -5 with price_var LastTraded.
    price_offset: Optional[float] = None
    side: Optional[str] = None          # contract side: "yes" | "no"
    order_action: Optional[str] = None  # LIMIT order direction: "buy" | "sell"
    var_name: Optional[str] = None
    value: Optional[str] = None
    message: Optional[str] = None
    line: Optional[int] = None
    line_var: Optional[str] = None
    # PAUSE: duration in milliseconds (literal or ms_var).
    ms: Optional[int] = None
    ms_var: Optional[str] = None
    # CANCEL_STALE: cancel resting limit orders older than this many ms.
    max_age_ms: Optional[int] = None
    max_age_ms_var: Optional[str] = None
    fired_line: Optional[int] = None


class EvaluationResult(BaseModel):
    action: Optional[Action] = None
    fired_line: Optional[int] = None
    stop: bool = False
    goto_line: Optional[int] = None


class MarketSnapshot(BaseModel):
    ticker: str
    yes_price: Optional[float] = None
    no_price: Optional[float] = None
    yes_bid_pct: Optional[float] = None
    yes_ask_pct: Optional[float] = None
    no_bid_pct: Optional[float] = None
    no_ask_pct: Optional[float] = None
    last_traded: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    minutes_to_expiry: Optional[float] = None
    distance_from_strike: Optional[float] = None
    volume: Optional[int] = None
    title: Optional[str] = None


class RiskLimitError(Exception):
    pass


class InfiniteLoopError(Exception):
    pass
