# Path: mat_acc/ratio_check/values/formula_eval.py
"""
Formula Evaluator

Evaluates simple arithmetic formulas using component values.
Shared by composite resolution, fallback formulas, and recompute.
"""

from typing import Optional, Dict


def evaluate_formula(
    formula: str,
    match_lookup: Dict,
) -> Optional[float]:
    """
    Evaluate a simple arithmetic formula using component values.

    Handles: a + b, a - b, a / b, a + b + c + d

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

        component = match_lookup.get(token)
        if not component or component.value is None:
            return None

        val = component.value
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


__all__ = ['evaluate_formula']
