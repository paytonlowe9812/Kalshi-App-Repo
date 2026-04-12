import json

from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.engine.actions import _resolve_ms
from backend.models import SimulationRequest, SimulationResponse, SimulationStep

router = APIRouter(prefix="/api/simulator", tags=["simulator"])

OPERATOR_MAP = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "lt": lambda a, b: a < b,
    "gte": lambda a, b: a >= b,
    "lte": lambda a, b: a <= b,
}


def _resolve_operand(val: str, variables: dict) -> float:
    if val in variables:
        return variables[val]
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


@router.post("/run")
def run_simulation(data: SimulationRequest):
    db = get_db()
    rules = db.execute(
        "SELECT * FROM rules WHERE bot_id = ? ORDER BY line_number",
        (data.bot_id,),
    ).fetchall()
    if not rules:
        raise HTTPException(400, "No rules defined for this bot")

    variables = {
        "YES_price": 50.0,
        "NO_price": 50.0,
        "PositionSize": 0.0,
        "HasPosition": 0.0,
        "AbsPositionSize": 0.0,
        "RestingLimitCount": 0.0,
        "OldestRestingLimitAgeSec": 0.0,
    }
    user_vars = db.execute(
        "SELECT name, value FROM variables WHERE bot_id = ?", (data.bot_id,)
    ).fetchall()
    for v in user_vars:
        try:
            variables[v["name"]] = float(v["value"])
        except (ValueError, TypeError):
            variables[v["name"]] = 0.0

    variables.update(data.variable_overrides)

    steps = []
    line_index = 0
    visit_counts: dict[int, int] = {}
    final_action = None
    condition_met = False
    in_condition_chain = False
    rules_list = [dict(r) for r in rules]

    while line_index < len(rules_list):
        rule = rules_list[line_index]
        ln = rule["line_number"]

        visit_counts[ln] = visit_counts.get(ln, 0) + 1
        if visit_counts[ln] > 100:
            steps.append(SimulationStep(
                line_number=ln, result="stopped", reason="Infinite loop detected"
            ))
            break

        lt = rule["line_type"]

        if lt in ("IF", "AND", "OR"):
            left = _resolve_operand(rule.get("left_operand", "0"), variables)
            right = _resolve_operand(rule.get("right_operand", "0"), variables)
            op = rule.get("operator", "eq")
            op_fn = OPERATOR_MAP.get(op, lambda a, b: False)
            result = op_fn(left, right)

            if lt == "IF":
                condition_met = (condition_met and result) if in_condition_chain else result
            elif lt == "AND":
                condition_met = (condition_met and result) if in_condition_chain else result
            elif lt == "OR":
                condition_met = (condition_met or result) if in_condition_chain else result
            in_condition_chain = True

            left_name = rule.get("left_operand", "?")
            right_name = rule.get("right_operand", "?")
            op_symbol = {"eq": "=", "neq": "!=", "gt": ">", "lt": "<", "gte": ">=", "lte": "<="}.get(op, op)

            steps.append(SimulationStep(
                line_number=ln,
                result="hit" if result else "skipped",
                reason=f"{left_name} ({left}) {op_symbol} {right_name} ({right})",
            ))
            line_index += 1

        elif lt == "THEN":
            if condition_met:
                action_type = rule.get("action_type", "")
                action = {"type": action_type}
                try:
                    params = json.loads(rule.get("action_params", "{}") or "{}")
                except (ValueError, TypeError):
                    params = {}
                action.update(params)
                reason = f"Action: {action_type}"
                if action_type == "PAUSE":
                    ms = _resolve_ms(
                        params.get("ms_var"), params.get("ms"), variables, 0, "PAUSE"
                    )
                    reason = f"Action: PAUSE ({ms} ms, simulated, no wall-clock wait)"
                elif action_type == "CANCEL_STALE":
                    ms = _resolve_ms(
                        params.get("max_age_ms_var"),
                        params.get("max_age_ms"),
                        variables,
                        60_000,
                        "CANCEL_STALE",
                    )
                    reason = (
                        f"Action: CANCEL_STALE (would cancel limits older than {ms} ms)"
                    )
                steps.append(SimulationStep(
                    line_number=ln, result="hit",
                    reason=reason,
                    action_fired=action,
                ))
                final_action = action

                if action_type == "SET_VAR" and "var_name" in params:
                    variables[params["var_name"]] = float(params.get("value", 0))
                elif action_type == "STOP":
                    line_index += 1
                    break
            else:
                steps.append(SimulationStep(
                    line_number=ln, result="skipped", reason="Condition not met"
                ))
            in_condition_chain = False
            line_index += 1

        elif lt == "ELSE":
            if not condition_met:
                action_type = rule.get("action_type", "")
                try:
                    params = json.loads(rule.get("action_params", "{}") or "{}")
                except (ValueError, TypeError):
                    params = {}
                action = (
                    {"type": action_type, **params} if action_type else None
                )
                reason = f"Else branch: {action_type}"
                if action_type == "PAUSE":
                    ms = _resolve_ms(
                        params.get("ms_var"), params.get("ms"), variables, 0, "PAUSE"
                    )
                    reason = f"Else branch: PAUSE ({ms} ms, simulated, no wall-clock wait)"
                elif action_type == "CANCEL_STALE":
                    ms = _resolve_ms(
                        params.get("max_age_ms_var"),
                        params.get("max_age_ms"),
                        variables,
                        60_000,
                        "CANCEL_STALE",
                    )
                    reason = (
                        f"Else branch: CANCEL_STALE (limits older than {ms} ms)"
                    )
                steps.append(SimulationStep(
                    line_number=ln, result="hit",
                    reason=reason,
                    action_fired=action,
                ))
                if action_type:
                    final_action = action
            else:
                steps.append(SimulationStep(
                    line_number=ln, result="skipped", reason="Condition was met"
                ))
            in_condition_chain = False
            line_index += 1

        elif lt == "GOTO":
            try:
                params = json.loads(rule.get("action_params", "{}") or "{}")
            except (ValueError, TypeError):
                params = {}
            target = params.get("line", 0)
            steps.append(SimulationStep(
                line_number=ln, result="branched",
                reason=f"Go to line {target}",
                goto_line=target,
            ))
            target_idx = next(
                (i for i, r in enumerate(rules_list) if r["line_number"] == target),
                None,
            )
            if target_idx is not None:
                line_index = target_idx
            else:
                line_index += 1
            in_condition_chain = False

        elif lt == "STOP":
            steps.append(SimulationStep(
                line_number=ln, result="stopped", reason="Bot stopped"
            ))
            break

        elif lt == "CONTINUE":
            steps.append(SimulationStep(
                line_number=ln, result="hit", reason="Continue to next iteration"
            ))
            break

        elif lt in ("LOG", "ALERT", "SET_VAR", "NOOP", "PAUSE", "CANCEL_STALE"):
            reason = f"{lt} executed"
            if lt == "PAUSE":
                try:
                    p = json.loads(rule.get("action_params", "{}") or "{}")
                except (ValueError, TypeError):
                    p = {}
                ms = _resolve_ms(p.get("ms_var"), p.get("ms"), variables, 0, "PAUSE")
                reason = f"PAUSE {ms} ms (simulated, no wall-clock wait)"
            elif lt == "NOOP":
                reason = "NOOP (no effect)"
            elif lt == "CANCEL_STALE":
                try:
                    p = json.loads(rule.get("action_params", "{}") or "{}")
                except (ValueError, TypeError):
                    p = {}
                ms = _resolve_ms(
                    p.get("max_age_ms_var"),
                    p.get("max_age_ms"),
                    variables,
                    60_000,
                    "CANCEL_STALE",
                )
                reason = f"CANCEL_STALE (limits older than {ms} ms, simulated)"
            steps.append(SimulationStep(
                line_number=ln, result="hit", reason=reason
            ))
            in_condition_chain = False
            line_index += 1

        else:
            steps.append(SimulationStep(
                line_number=ln, result="skipped", reason=f"Unknown type: {lt}"
            ))
            in_condition_chain = False
            line_index += 1

    return SimulationResponse(
        steps=steps,
        final_action=final_action,
        variables_after={k: float(v) if isinstance(v, (int, float)) else 0.0 for k, v in variables.items()},
    )
