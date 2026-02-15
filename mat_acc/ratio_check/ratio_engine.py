# Path: mat_acc/ratio_check/ratio_engine.py
"""
Ratio Engine

Calculates financial ratios from matched component values.
Handles both simple (single component) and complex (multi-component)
numerator/denominator definitions.
"""

from typing import Dict, List, Any, Optional

from core.logger.ipo_logging import get_process_logger

from .ratio_models import ComponentMatch, RatioResult
from .ratio_definitions import STANDARD_RATIOS


logger = get_process_logger('ratio_engine')


def calculate_ratios(
    component_matches: List[ComponentMatch],
    ratio_list: Optional[List[Dict[str, Any]]] = None,
) -> List[RatioResult]:
    """
    Calculate financial ratios from matched components.

    Args:
        component_matches: List of matched components with values
        ratio_list: Optional filtered list of ratio definitions.
                    If None, uses STANDARD_RATIOS (backward compatible).

    Returns:
        List of RatioResult
    """
    if ratio_list is None:
        ratio_list = STANDARD_RATIOS

    matched_lookup: Dict[str, ComponentMatch] = {
        m.component_name: m for m in component_matches if m.matched
    }

    ratios = []
    for ratio_def in ratio_list:
        ratio = _calculate_single_ratio(ratio_def, matched_lookup)
        ratios.append(ratio)

    return ratios


def _calculate_single_ratio(
    ratio_def: Dict[str, Any],
    matched_lookup: Dict[str, ComponentMatch],
) -> RatioResult:
    """Calculate a single ratio from its definition."""
    ratio = RatioResult(
        ratio_name=ratio_def['name'],
        formula=ratio_def['formula'],
    )

    # Get numerator
    num_result = _resolve_component_value(
        ratio_def['numerator'], matched_lookup
    )
    if num_result['error']:
        ratio.numerator = num_result['formula']
        ratio.error = num_result['error']
        return ratio

    ratio.numerator = num_result['formula']
    ratio.numerator_value = num_result['value']

    # Get denominator
    den_result = _resolve_component_value(
        ratio_def['denominator'], matched_lookup
    )
    if den_result['error']:
        ratio.denominator = den_result['formula']
        ratio.error = den_result['error']
        return ratio

    ratio.denominator = den_result['formula']
    ratio.denominator_value = den_result['value']

    # Calculate ratio
    if ratio.numerator_value is not None and ratio.denominator_value is not None:
        if ratio.denominator_value != 0:
            ratio.value = ratio.numerator_value / ratio.denominator_value
            ratio.valid = True
        else:
            ratio.error = "Division by zero"
    else:
        ratio.error = "Values not available for matched components"

    return ratio


def _resolve_component_value(
    component_def: Any,
    matched_lookup: Dict[str, ComponentMatch],
) -> Dict[str, Any]:
    """
    Resolve a component definition to its numeric value.

    Simple: 'current_assets' -> single component lookup
    Complex: ['current_assets', '-inventory'] -> current_assets - inventory
    """
    if isinstance(component_def, str):
        return _resolve_simple(component_def, matched_lookup)
    elif isinstance(component_def, list):
        return _resolve_complex(component_def, matched_lookup)
    else:
        return {
            'value': None,
            'formula': str(component_def),
            'error': f"Invalid component type: {type(component_def)}",
        }


def _resolve_simple(
    component_name: str,
    matched_lookup: Dict[str, ComponentMatch],
) -> Dict[str, Any]:
    """Resolve a single component to its value."""
    if component_name in matched_lookup:
        match = matched_lookup[component_name]
        return {
            'value': match.value,
            'formula': component_name,
            'error': None,
        }
    return {
        'value': None,
        'formula': component_name,
        'error': f"Component '{component_name}' not matched",
    }


def _resolve_complex(
    component_list: List[str],
    matched_lookup: Dict[str, ComponentMatch],
) -> Dict[str, Any]:
    """Resolve a multi-component expression to its value."""
    total_value = None
    formula_parts = []
    missing = []

    for item in component_list:
        if item.startswith('-'):
            operator = -1
            name = item[1:]
            formula_parts.append(f"- {name}")
        elif item.startswith('+'):
            operator = 1
            name = item[1:]
            formula_parts.append(f"+ {name}")
        else:
            operator = 1
            name = item
            if formula_parts:
                formula_parts.append(f"+ {name}")
            else:
                formula_parts.append(name)

        if name in matched_lookup:
            match = matched_lookup[name]
            if match.value is not None:
                if total_value is None:
                    total_value = 0.0
                total_value += operator * match.value
            else:
                missing.append(f"{name} (no value)")
        else:
            missing.append(f"{name} (not matched)")

    formula = ' '.join(formula_parts)

    if missing:
        return {
            'value': total_value,
            'formula': formula,
            'error': f"Missing: {', '.join(missing)}",
        }

    return {'value': total_value, 'formula': formula, 'error': None}


__all__ = ['calculate_ratios']
