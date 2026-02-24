# Path: mat_acc/ratio_check/values/formula_eval.py
"""
Formula Evaluator

Evaluates simple arithmetic formulas using component values.
Shared by composite resolution, fallback formulas, and recompute.

Supports abs: prefix on component names to use absolute value,
mirroring the pattern in ratio_engine.py. This is essential for
add-back formulas (e.g. EBITDA) where components like interest
expense must contribute their magnitude regardless of sign.
"""

from typing import Optional, Dict


def evaluate_formula(
    formula: str,
    match_lookup: Dict,
) -> Optional[float]:
    """
    Evaluate a simple arithmetic formula using component values.

    Handles: a + b, a - b, a / b, a + b + c + d
    Supports abs: prefix (e.g. "net_income + abs:interest_expense")

    Args:
        formula: Formula string (e.g., "total_assets - total_equity")
        match_lookup: Component name to ComponentMatch mapping

    Returns:
        Computed value or None if any component missing
    """
    tokens = formula.replace('+', ' + ').replace(
        '-', ' - '
    ).replace('/', ' / ').split()

    result = None
    operator = '+'

    for token in tokens:
        if token in ('+', '-', '/'):
            operator = token
            continue

        val = _resolve_token(token, match_lookup)
        if val is None:
            return None

        if result is None:
            result = val if operator == '+' else -val
        elif operator == '+':
            result += val
        elif operator == '-':
            result -= val
        elif operator == '/' and val != 0:
            result /= val
        else:
            return None

    return result


def _resolve_token(token: str, match_lookup: Dict) -> Optional[float]:
    """Resolve a formula token to its numeric value.

    Handles abs: prefix for magnitude-only semantics.
    """
    use_abs = False
    lookup_name = token
    if token.startswith('abs:'):
        use_abs = True
        lookup_name = token[4:]

    component = match_lookup.get(lookup_name)
    if not component or component.value is None:
        return None

    val = component.value
    if use_abs:
        val = abs(val)
    return val


__all__ = ['evaluate_formula']
