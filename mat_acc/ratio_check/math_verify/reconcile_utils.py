# Path: mat_acc/ratio_check/math_verify/reconcile_utils.py
"""
Reconciliation Utilities

Shared helpers for the fact reconciler:
- QName-aware value lookup across namespace formats
- Scale factor detection (power-of-10 differences)
"""

import math
from typing import Optional

from core.qname import parse_qname


# How close log10(ratio) must be to an integer to count as scale
_SCALE_DETECT_TOLERANCE = 0.15


def lookup_value(
    concept: str, values: dict[str, float],
) -> Optional[float]:
    """
    Look up a concept value with namespace-aware key matching.

    Tier 1: Exact match
    Tier 2: Alternate separator (colon <-> underscore)
    Tier 3: Namespace-aware normalized match
        - If query has namespace: require namespace match
        - If no namespace: match only if unambiguous
    Never returns a value from a different namespace.
    """
    # Tier 1: Exact match
    if concept in values:
        return values[concept]

    # Tier 2: Alternate separator (colon <-> underscore)
    if ':' in concept:
        alt_key = concept.replace(':', '_', 1)
        if alt_key in values:
            return values[alt_key]
    elif '_' in concept:
        parts = concept.rsplit('_', 1)
        if len(parts) == 2 and parts[1] and parts[1][0].isupper():
            alt_key = parts[0] + ':' + parts[1]
            if alt_key in values:
                return values[alt_key]

    # Tier 3: Namespace-aware normalized match
    ns, local = parse_qname(concept)
    if not local:
        return None

    if ns:
        for key, val in values.items():
            k_ns, k_local = parse_qname(key)
            if k_local == local and k_ns.lower() == ns.lower():
                return val
        return None

    # No namespace - match only if unambiguous (1 match)
    matches = []
    for key, val in values.items():
        k_ns, k_local = parse_qname(key)
        if k_local == local:
            matches.append(val)

    if len(matches) == 1:
        return matches[0]

    return None


def detect_scale_factor(
    ixbrl_val: float, parsed_val: float,
) -> int:
    """
    Detect power-of-10 difference between values.

    Returns the integer N where ixbrl_val ~ parsed_val * 10^N.
    Returns 0 if values are in the same scale.
    """
    if ixbrl_val == 0 or parsed_val == 0:
        return 0

    ratio = abs(ixbrl_val / parsed_val)
    if ratio == 0:
        return 0

    log_ratio = math.log10(ratio)
    rounded = round(log_ratio)

    if rounded == 0:
        return 0
    if abs(log_ratio - rounded) < _SCALE_DETECT_TOLERANCE:
        return rounded

    return 0


__all__ = ['lookup_value', 'detect_scale_factor']
