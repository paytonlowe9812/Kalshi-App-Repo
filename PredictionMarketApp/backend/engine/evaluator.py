import json
from backend.database import get_db
from backend.models import Action, EvaluationResult, InfiniteLoopError

OPERATOR_MAP = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "lt": lambda a, b: a < b,
    "gte": lambda a, b: a >= b,
    "lte": lambda a, b: a <= b,
}

INFINITE_LOOP_THRESHOLD = 100


def _resolve_operand(val: str, variables: dict) -> float:
    if val and val in variables:
        return variables[val]
    try:
        return float(val) if val else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_action(rule: dict) -> Action | None:
    action_type = rule.get("action_type")
    if not action_type:
        return None
    try:
        params = json.loads(rule.get("action_params") or "{}")
    except (ValueError, TypeError):
        params = {}
    return Action(
        type=action_type,
        contracts=params.get("contracts"),
        contracts_var=params.get("contracts_var"),
        price=params.get("price"),
        price_var=params.get("price_var"),
        side=params.get("side"),
        var_name=params.get("var_name"),
        value=params.get("value"),
        message=params.get("message"),
        line=params.get("line"),
        line_var=params.get("line_var"),
        fired_line=rule.get("line_number"),
    )


def evaluate(bot_id: int, variables: dict) -> EvaluationResult:
    db = get_db()
    rules = db.execute(
        "SELECT * FROM rules WHERE bot_id = ? ORDER BY line_number", (bot_id,)
    ).fetchall()
    rules_list = [dict(r) for r in rules]

    if not rules_list:
        return EvaluationResult()

    line_index = 0
    visit_counts: dict[int, int] = {}
    condition_met = False

    while line_index < len(rules_list):
        rule = rules_list[line_index]
        ln = rule["line_number"]

        visit_counts[ln] = visit_counts.get(ln, 0) + 1
        if visit_counts[ln] > INFINITE_LOOP_THRESHOLD:
            raise InfiniteLoopError()

        lt = rule["line_type"]

        if lt in ("IF", "AND", "OR"):
            left = _resolve_operand(rule.get("left_operand"), variables)
            right = _resolve_operand(rule.get("right_operand"), variables)
            op_fn = OPERATOR_MAP.get(rule.get("operator", "eq"), lambda a, b: False)
            result = op_fn(left, right)

            if lt == "IF":
                condition_met = result
            elif lt == "AND":
                condition_met = condition_met and result
            elif lt == "OR":
                condition_met = condition_met or result
            line_index += 1

        elif lt == "THEN":
            if condition_met:
                action = _parse_action(rule)
                if action:
                    action.fired_line = ln
                    return EvaluationResult(action=action, fired_line=ln)
            line_index += 1

        elif lt == "ELSE":
            if not condition_met:
                action = _parse_action(rule)
                if action:
                    action.fired_line = ln
                    return EvaluationResult(action=action, fired_line=ln)
            line_index += 1

        elif lt == "GOTO":
            try:
                params = json.loads(rule.get("action_params") or "{}")
            except (ValueError, TypeError):
                params = {}
            line_var = (str(params.get("line_var") or "")).strip()
            if line_var and line_var in variables:
                try:
                    target = int(round(float(variables[line_var])))
                except (TypeError, ValueError):
                    target = params.get("line", 0)
            else:
                target = params.get("line", 0)
            target_idx = next(
                (i for i, r in enumerate(rules_list) if r["line_number"] == target),
                None,
            )
            if target_idx is not None:
                line_index = target_idx
            else:
                line_index += 1

        elif lt == "STOP":
            return EvaluationResult(
                action=Action(type="STOP", fired_line=ln), fired_line=ln
            )

        elif lt == "CONTINUE":
            return EvaluationResult()

        elif lt == "SET_VAR":
            action = _parse_action(rule)
            if action:
                action.fired_line = ln
                return EvaluationResult(action=action, fired_line=ln)
            line_index += 1

        elif lt in ("LOG", "ALERT"):
            action = _parse_action(rule)
            if action:
                action.fired_line = ln
                return EvaluationResult(action=action, fired_line=ln)
            line_index += 1

        else:
            line_index += 1

    return EvaluationResult()
