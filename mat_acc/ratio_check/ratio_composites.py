# Path: mat_acc/ratio_check/ratio_composites.py
"""
Composite Ratio Calculators

Handles non-standard ratio calculations that go beyond simple
numerator/denominator division: absolute values, multi-factor
products, weighted composites, and derived intermediate values.

Each calculator returns a RatioResult matching the standard interface.
"""

from typing import Any, Callable, Dict, Optional

from .ratio_models import ComponentMatch, RatioResult


def _get_value(
    name: str,
    lookup: Dict[str, ComponentMatch],
) -> Optional[float]:
    """Get a component value from lookup, or None."""
    match = lookup.get(name)
    if match is not None and match.value is not None:
        return match.value
    return None


def _missing_components(
    names: list,
    lookup: Dict[str, ComponentMatch],
) -> list:
    """Return names of components that are missing or have no value."""
    return [n for n in names if _get_value(n, lookup) is None]


def calculate_absolute(
    ratio_def: Dict[str, Any],
    matched_lookup: Dict[str, ComponentMatch],
) -> RatioResult:
    """Evaluate numerator expression only (no division)."""
    from .ratio_engine import _resolve_component_value
    ratio = RatioResult(
        ratio_name=ratio_def['name'],
        formula=ratio_def['formula'],
    )
    num_result = _resolve_component_value(
        ratio_def['numerator'], matched_lookup,
    )
    if num_result['error']:
        ratio.numerator = num_result['formula']
        ratio.error = num_result['error']
        return ratio
    ratio.numerator = num_result['formula']
    ratio.numerator_value = num_result['value']
    ratio.value = num_result['value']
    ratio.valid = ratio.value is not None
    return ratio


def calculate_roic(
    ratio_def: Dict[str, Any],
    matched_lookup: Dict[str, ComponentMatch],
) -> RatioResult:
    """
    Return on Invested Capital.

    NOPAT = Operating Income * (1 - Effective Tax Rate)
    Effective Tax Rate = Income Tax Expense / Income Before Tax
    Invested Capital = Total Equity + Total Debt - Cash
    ROIC = NOPAT / Invested Capital
    """
    ratio = RatioResult(
        ratio_name=ratio_def['name'],
        formula=ratio_def['formula'],
    )
    needed = [
        'operating_income', 'income_tax_expense',
        'income_before_tax', 'total_equity',
    ]
    missing = _missing_components(needed, matched_lookup)
    if missing:
        ratio.error = f"Missing: {', '.join(missing)}"
        return ratio

    oi = _get_value('operating_income', matched_lookup)
    tax = _get_value('income_tax_expense', matched_lookup)
    ebt = _get_value('income_before_tax', matched_lookup)
    equity = _get_value('total_equity', matched_lookup)
    debt = _get_value('total_debt', matched_lookup) or 0.0
    cash = _get_value('cash_and_equivalents', matched_lookup) or 0.0

    if ebt == 0:
        ratio.error = "Income before tax is zero"
        return ratio

    eff_tax_rate = abs(tax) / abs(ebt) if ebt != 0 else 0.0
    nopat = oi * (1.0 - eff_tax_rate)
    invested_capital = equity + debt - cash

    ratio.numerator = 'NOPAT'
    ratio.numerator_value = nopat
    ratio.denominator = 'Invested Capital'
    ratio.denominator_value = invested_capital

    if invested_capital == 0:
        ratio.error = "Invested capital is zero"
        return ratio

    ratio.value = nopat / invested_capital
    ratio.valid = True
    return ratio


def calculate_dupont(
    ratio_def: Dict[str, Any],
    matched_lookup: Dict[str, ComponentMatch],
) -> RatioResult:
    """
    DuPont 5-Factor ROE decomposition.

    ROE = (NI/EBT) * (EBT/EBIT) * (EBIT/Rev) * (Rev/TA) * (TA/Eq)
    """
    ratio = RatioResult(
        ratio_name=ratio_def['name'],
        formula=ratio_def['formula'],
    )
    needed = [
        'net_income', 'income_before_tax', 'operating_income',
        'revenue', 'total_assets', 'total_equity',
    ]
    missing = _missing_components(needed, matched_lookup)
    if missing:
        ratio.error = f"Missing: {', '.join(missing)}"
        return ratio

    ni = _get_value('net_income', matched_lookup)
    ebt = _get_value('income_before_tax', matched_lookup)
    ebit = _get_value('operating_income', matched_lookup)
    rev = _get_value('revenue', matched_lookup)
    ta = _get_value('total_assets', matched_lookup)
    eq = _get_value('total_equity', matched_lookup)

    zeros = []
    if ebt == 0:
        zeros.append('income_before_tax')
    if ebit == 0:
        zeros.append('operating_income')
    if rev == 0:
        zeros.append('revenue')
    if ta == 0:
        zeros.append('total_assets')
    if eq == 0:
        zeros.append('total_equity')
    if zeros:
        ratio.error = f"Zero value: {', '.join(zeros)}"
        return ratio

    product = (ni / ebt) * (ebt / ebit) * (ebit / rev)
    product *= (rev / ta) * (ta / eq)

    ratio.numerator = 'NI/EBT * EBT/EBIT * EBIT/Rev'
    ratio.denominator = 'Rev/TA * TA/Eq'
    ratio.value = product
    ratio.valid = True
    return ratio


def calculate_altman_z(
    ratio_def: Dict[str, Any],
    matched_lookup: Dict[str, ComponentMatch],
) -> RatioResult:
    """
    Altman Z-Score for bankruptcy prediction.

    Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
    A = Working Capital / Total Assets
    B = Retained Earnings / Total Assets
    C = EBIT / Total Assets
    D = Equity / Total Liabilities  (book value proxy)
    E = Revenue / Total Assets
    """
    ratio = RatioResult(
        ratio_name=ratio_def['name'],
        formula=ratio_def['formula'],
    )
    needed = [
        'current_assets', 'current_liabilities', 'retained_earnings',
        'total_assets', 'operating_income', 'total_equity',
        'total_liabilities', 'revenue',
    ]
    missing = _missing_components(needed, matched_lookup)
    if missing:
        ratio.error = f"Missing: {', '.join(missing)}"
        return ratio

    ca = _get_value('current_assets', matched_lookup)
    cl = _get_value('current_liabilities', matched_lookup)
    re = _get_value('retained_earnings', matched_lookup)
    ta = _get_value('total_assets', matched_lookup)
    ebit = _get_value('operating_income', matched_lookup)
    eq = _get_value('total_equity', matched_lookup)
    tl = _get_value('total_liabilities', matched_lookup)
    rev = _get_value('revenue', matched_lookup)

    if ta == 0:
        ratio.error = "Total assets is zero"
        return ratio
    if tl == 0:
        ratio.error = "Total liabilities is zero"
        return ratio

    wc = ca - cl
    a_term = 1.2 * (wc / ta)
    b_term = 1.4 * (re / ta)
    c_term = 3.3 * (ebit / ta)
    d_term = 0.6 * (eq / tl)
    e_term = 1.0 * (rev / ta)

    z_score = a_term + b_term + c_term + d_term + e_term

    ratio.numerator = f"A={a_term:.3f} B={b_term:.3f} C={c_term:.3f}"
    ratio.denominator = f"D={d_term:.3f} E={e_term:.3f}"
    ratio.value = z_score
    ratio.valid = True
    return ratio


# Registry mapping calculation_type -> calculator function
COMPOSITE_CALCULATORS: Dict[str, Callable] = {
    'absolute': calculate_absolute,
    'roic': calculate_roic,
    'dupont': calculate_dupont,
    'altman_z': calculate_altman_z,
}


__all__ = ['COMPOSITE_CALCULATORS']
