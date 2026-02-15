# Path: mat_acc/ratio_check/match_verify/qualifier_rules.py
"""
Qualifier Rules

Detects semantic qualifiers in concept names that indicate
whether a concept is the right match for a component.

Examples of qualifiers:
  - 'Current' vs 'Noncurrent' (temporal scope)
  - 'IncurredButNotYetPaid' (accrual, not cash flow)
  - 'ExcludingXXX' (partial measure)
  - 'IncludingXXX' (broader measure)

Also checks statement placement: a capex concept from
supplemental disclosures should not beat one from investing.
"""

from core.logger.ipo_logging import get_process_logger


logger = get_process_logger('qualifier_rules')


# Components that MUST be noncurrent (reject 'Current' suffix)
NONCURRENT_COMPONENTS = {
    'long_term_debt',
}

# Components that MUST be current (reject 'Noncurrent' suffix)
CURRENT_COMPONENTS = {
    'current_assets',
    'current_liabilities',
    'short_term_debt',
    'accounts_receivable',
    'accounts_payable',
    'cash_and_equivalents',
    'inventory',
}

# Concept name fragments that indicate supplemental/disclosure
# items, NOT primary statement line items
SUPPLEMENTAL_MARKERS = [
    'incurredbutnotyetpaid',
    'supplementalschedule',
    'supplementaldisclosure',
    'paidduringperiod',
]

# Components that should come from specific statement types.
# 'cash_flow' = should appear under operating/investing/financing
CASH_FLOW_COMPONENTS = {
    'capital_expenditures',
    'operating_cash_flow',
    'depreciation_amortization',
}

# Balance sheet components (should be instant-period concepts)
BALANCE_SHEET_COMPONENTS = {
    'total_assets',
    'total_liabilities',
    'total_equity',
    'current_assets',
    'current_liabilities',
    'long_term_debt',
    'short_term_debt',
    'total_debt',
    'inventory',
    'cash_and_equivalents',
    'accounts_receivable',
    'accounts_payable',
}

# Income statement components (should be duration-period concepts)
INCOME_COMPONENTS = {
    'revenue',
    'cost_of_goods_sold',
    'gross_profit',
    'operating_income',
    'net_income',
    'income_before_tax',
    'income_tax_expense',
    'interest_expense',
    'ebitda',
    'earnings_per_share',
}


def check_qualifier(
    component_id: str,
    concept_local_name: str,
) -> dict:
    """
    Check if a concept's qualifiers are compatible with the component.

    Args:
        component_id: The component being matched
        concept_local_name: Local name of the matched concept

    Returns:
        dict with 'valid' (bool), 'reason' (str or None),
        'penalty' (int, score reduction if borderline)
    """
    name_lower = concept_local_name.lower()
    result = {'valid': True, 'reason': None, 'penalty': 0}

    # Check noncurrent components for 'Current' suffix trap
    if component_id in NONCURRENT_COMPONENTS:
        result = _check_noncurrent(component_id, name_lower)
        if not result['valid']:
            return result

    # Check supplemental markers (all components, not just cash flow)
    result = _check_supplemental(component_id, name_lower)
    if not result['valid']:
        return result

    # Check period type alignment
    period_result = _check_period_alignment(
        component_id, name_lower,
    )
    if period_result['penalty'] > 0:
        result['penalty'] = max(result['penalty'], period_result['penalty'])

    return result


def _check_noncurrent(component_id: str, name_lower: str) -> dict:
    """Reject current-portion concepts for noncurrent components."""
    # Patterns indicating current portion
    current_traps = [
        'current',
    ]
    noncurrent_safe = [
        'noncurrent',
        'longterm',
        'long-term',
    ]

    # First check if it's clearly noncurrent (safe)
    for safe in noncurrent_safe:
        if safe in name_lower:
            return {'valid': True, 'reason': None, 'penalty': 0}

    # Check if name ends with 'current' (the trap)
    # Must avoid matching 'noncurrent' which contains 'current'
    stripped = name_lower.replace('noncurrent', '')
    if stripped.endswith('current'):
        return {
            'valid': False,
            'reason': (
                f"'{component_id}' needs noncurrent, "
                f"but concept has 'Current' suffix"
            ),
            'penalty': 0,
        }

    return {'valid': True, 'reason': None, 'penalty': 0}


def _check_supplemental(component_id: str, name_lower: str) -> dict:
    """Reject supplemental disclosure concepts for primary items."""
    for marker in SUPPLEMENTAL_MARKERS:
        if marker in name_lower:
            return {
                'valid': False,
                'reason': (
                    f"'{component_id}' is primary item, but concept "
                    f"is supplemental (contains '{marker}')"
                ),
                'penalty': 0,
            }
    return {'valid': True, 'reason': None, 'penalty': 0}


def _check_period_alignment(
    component_id: str,
    name_lower: str,
) -> dict:
    """
    Check period type alignment (instant vs duration).

    Balance sheet items are instant, income items are duration.
    This is a soft check (penalty, not rejection) because
    concept names don't always indicate period type.
    """
    # 'IncreaseDecrease' pattern = duration (change over period)
    # If a balance sheet component matches an IncreaseDecrease
    # concept, apply a penalty
    if component_id in BALANCE_SHEET_COMPONENTS:
        if 'increasedecrease' in name_lower:
            return {
                'valid': True,
                'reason': None,
                'penalty': 15,
            }

    return {'valid': True, 'reason': None, 'penalty': 0}


__all__ = [
    'check_qualifier',
    'NONCURRENT_COMPONENTS',
    'CURRENT_COMPONENTS',
    'BALANCE_SHEET_COMPONENTS',
    'INCOME_COMPONENTS',
    'CASH_FLOW_COMPONENTS',
]
