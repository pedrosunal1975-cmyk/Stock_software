# Path: mat_acc/ratio_check/match_verify/plausibility_checks.py
"""
Plausibility Checks

Cross-component value validation.
After all components have values, checks whether matched values
are financially plausible relative to each other.

Rules are universal (no company-specific logic).
Returns flags for implausible matches that should try alternatives.
"""

from typing import Optional

from core.logger.ipo_logging import get_process_logger


logger = get_process_logger('plausibility_checks')


# Minimum fraction rules: component X should be at least Y% of
# component Z. If below, the match is implausible.
# Format: (component, reference, min_fraction, max_fraction)
# None means no limit on that side.
RATIO_BOUNDS = [
    # long_term_debt should be meaningful vs total_liabilities
    ('long_term_debt', 'total_liabilities', 0.01, None),
    # short_term_debt should be meaningful vs current_liabilities
    ('short_term_debt', 'current_liabilities', 0.005, None),
    # capex should be meaningful vs total_assets
    ('capital_expenditures', 'total_assets', 0.001, 0.80),
    # interest_expense should be plausible vs long_term_debt
    # Implied rate: 0.1% to 30% (very generous bounds)
    ('interest_expense', 'long_term_debt', 0.001, 0.30),
    # depreciation should be meaningful vs total_assets
    ('depreciation_amortization', 'total_assets', 0.001, 0.50),
    # operating_income vs revenue (generous: losses can exceed rev)
    ('operating_income', 'revenue', 0.001, 5.0),
    # net_income magnitude vs revenue (generous: losses can exceed)
    ('net_income', 'revenue', 0.0001, 5.0),
    # income_tax vs income_before_tax (0% to 200% for loss years)
    ('income_tax_expense', 'income_before_tax', 0.0, 2.0),
    # EPS sanity: vs net_income/shares (checked via magnitude)
    # earnings_per_share should be tiny vs revenue
    ('earnings_per_share', 'revenue', 0.0, 0.01),
]

# Subset rules: component X must be <= component Y
# ONLY include relationships that are ALWAYS true regardless of
# profitability or capital structure. Excluded:
#   COGS vs revenue: negative gross margin is legitimate
#   operating_income vs revenue: operating losses can exceed revenue
#   total_liabilities vs total_assets: negative equity is real
SUBSET_RULES = [
    ('current_assets', 'total_assets'),
    ('current_liabilities', 'total_liabilities'),
    ('cash_and_equivalents', 'current_assets'),
    ('inventory', 'current_assets'),
    ('accounts_receivable', 'current_assets'),
    ('accounts_payable', 'current_liabilities'),
    ('long_term_debt', 'total_liabilities'),
    ('short_term_debt', 'current_liabilities'),
    ('gross_profit', 'revenue'),
    ('interest_expense', 'total_liabilities'),
    ('income_tax_expense', 'revenue'),
]

# Sign expectations: some components should normally have
# a specific sign. Violations are warnings, not rejections.
SIGN_EXPECTATIONS = {
    'total_assets': 'positive',
    'revenue': 'positive',
    'cost_of_goods_sold': 'positive',
    'total_liabilities': 'positive',
    'capital_expenditures': 'positive',
    'interest_expense': 'positive',
    'depreciation_amortization': 'positive',
}


def check_plausibility(
    component_id: str,
    value: Optional[float],
    all_values: dict[str, Optional[float]],
) -> dict:
    """
    Check if a component's value is plausible.

    Args:
        component_id: Component being checked
        value: Its matched value
        all_values: All component values {component_id: value}

    Returns:
        dict with 'valid' (bool), 'reason' (str or None)
    """
    if value is None:
        return {'valid': True, 'reason': None}

    # Check ratio bounds
    for comp, ref, min_frac, max_frac in RATIO_BOUNDS:
        if comp != component_id:
            continue
        ref_val = all_values.get(ref)
        if ref_val is None or ref_val == 0:
            continue
        result = _check_ratio_bound(
            component_id, value, ref, ref_val,
            min_frac, max_frac,
        )
        if not result['valid']:
            return result

    # Check subset rules
    for child, parent in SUBSET_RULES:
        if child != component_id:
            continue
        parent_val = all_values.get(parent)
        if parent_val is None:
            continue
        result = _check_subset(
            component_id, value, parent, parent_val,
        )
        if not result['valid']:
            return result

    return {'valid': True, 'reason': None}


def _check_ratio_bound(
    component_id: str,
    value: float,
    ref_id: str,
    ref_value: float,
    min_frac: Optional[float],
    max_frac: Optional[float],
) -> dict:
    """Check if value/reference falls within expected bounds."""
    abs_value = abs(value)
    abs_ref = abs(ref_value)

    if abs_ref == 0:
        return {'valid': True, 'reason': None}

    fraction = abs_value / abs_ref

    if min_frac is not None and fraction < min_frac:
        pct = fraction * 100
        min_pct = min_frac * 100
        return {
            'valid': False,
            'reason': (
                f"'{component_id}' = {value:,.0f} is only "
                f"{pct:.2f}% of '{ref_id}' = {ref_value:,.0f} "
                f"(expected >= {min_pct:.1f}%)"
            ),
        }

    if max_frac is not None and fraction > max_frac:
        pct = fraction * 100
        max_pct = max_frac * 100
        return {
            'valid': False,
            'reason': (
                f"'{component_id}' = {value:,.0f} is "
                f"{pct:.1f}% of '{ref_id}' = {ref_value:,.0f} "
                f"(expected <= {max_pct:.1f}%)"
            ),
        }

    return {'valid': True, 'reason': None}


def _check_subset(
    child_id: str,
    child_value: float,
    parent_id: str,
    parent_value: float,
) -> dict:
    """Check that child <= parent (subset relationship)."""
    # Allow 5% tolerance for rounding
    if abs(child_value) > abs(parent_value) * 1.05:
        return {
            'valid': False,
            'reason': (
                f"'{child_id}' = {child_value:,.0f} exceeds "
                f"'{parent_id}' = {parent_value:,.0f} "
                f"(should be subset)"
            ),
        }
    return {'valid': True, 'reason': None}


__all__ = [
    'check_plausibility',
    'RATIO_BOUNDS',
    'SUBSET_RULES',
]
