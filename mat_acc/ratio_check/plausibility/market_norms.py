# Path: mat_acc/ratio_check/plausibility/market_norms.py
"""
Market Norms

Normative expected ranges for ratios and component proportions.
All values here are NORMATIVE (hardcoded accounting/math expectations).
Declared values from filings are handled by declared_resolver.py.

Market-specific norms override universal norms where they differ.
"""

from typing import Dict, Optional, Tuple


# -- Universal ratio ranges (all markets) --
# Format: ratio_name -> (warn_min, warn_max, basis_description)
# None means no bound in that direction.
UNIVERSAL_RATIO_RANGES: Dict[str, Tuple] = {
    'Current Ratio': (0.0, 15.0, 'accounting: must be non-negative'),
    'Quick Ratio': (-0.5, 15.0, 'near-zero or negative unusual'),
    'Cash Ratio': (0.0, 10.0, 'cash cannot be negative'),
    'Gross Margin': (-3.0, 1.0, 'above 100% is impossible'),
    'Operating Margin': (-10.0, 0.8, 'extreme margins flag errors'),
    'Net Profit Margin': (-10.0, 0.7, 'extreme margins flag errors'),
    'EBITDA Margin': (-10.0, 1.0, 'extreme margins flag errors'),
    'Debt to Equity': (-5.0, 30.0, 'extreme leverage unusual'),
    'Debt Ratio': (0.0, 1.5, 'above 1.0 means negative equity'),
    'Equity Multiplier': (0.5, 50.0, 'extreme values flag errors'),
    'Asset Turnover': (0.0, 10.0, 'cannot be negative'),
    'Inventory Turnover': (0.0, 500.0, 'cannot be negative'),
    'Receivables Turnover': (0.0, 200.0, 'cannot be negative'),
    'Return on Assets': (-5.0, 1.0, 'extreme ROA flags errors'),
    'Return on Equity': (-10.0, 5.0, 'extreme ROE flags errors'),
    'Days Inventory Outstanding': (0.0, 1000.0, 'cannot be negative'),
    'Days Sales Outstanding': (0.0, 500.0, 'cannot be negative'),
    'Days Payable Outstanding': (0.0, 500.0, 'cannot be negative'),
}

# -- Market-specific norms (override universal where different) --
# Effective tax rate varies significantly by jurisdiction.
MARKET_RATIO_RANGES: Dict[str, Dict[str, Tuple]] = {
    'sec': {
        'Effective Tax Rate': (
            -0.05, 0.40,
            'US federal 21% + state 0-13%',
        ),
    },
    'esef': {
        'Effective Tax Rate': (
            -0.05, 0.45,
            'EU member state range 9-33%',
        ),
    },
}


# -- Component proportion norms (component vs reference) --
# Format: (component, reference, min_pct, max_pct, basis)
PROPORTION_NORMS = [
    (
        'stock_based_compensation', 'selling_general_admin',
        0.005, 0.50,
        'SBC typically 0.5-50% of SG&A',
    ),
    (
        'depreciation_amortization', 'property_plant_equipment',
        0.02, 0.40,
        'D&A typically 2-40% of PP&E (annual)',
    ),
    (
        'interest_expense', 'long_term_debt',
        0.005, 0.20,
        'interest typically 0.5-20% of LTD',
    ),
    (
        'r_and_d_expense', 'revenue',
        0.001, 0.80,
        'R&D typically 0.1-80% of revenue',
    ),
    (
        'selling_general_admin', 'revenue',
        0.01, 2.0,
        'SG&A typically 1-200% of revenue',
    ),
    (
        'accounts_receivable', 'revenue',
        0.001, 1.0,
        'AR typically 0.1-100% of revenue',
    ),
    (
        'inventory', 'cost_of_goods_sold',
        0.01, 3.0,
        'inventory typically 1-300% of COGS',
    ),
]

# -- Scale anomaly threshold --
# If a matched component's absolute value is below this fraction
# of revenue AND the match confidence is low, flag it.
SCALE_ANOMALY_THRESHOLD = 0.0005  # 0.05% of revenue
SCALE_LOW_CONFIDENCE_CUTOFF = 35.0  # match score below this


def get_ratio_range(
    ratio_name: str, market: str,
) -> Optional[Tuple[Optional[float], Optional[float], str]]:
    """
    Get expected range for a ratio, market-aware.

    Returns (min, max, basis) or None if no norm exists.
    Market-specific norms override universal norms.
    """
    market_ranges = MARKET_RATIO_RANGES.get(market, {})
    if ratio_name in market_ranges:
        return market_ranges[ratio_name]
    if ratio_name in UNIVERSAL_RATIO_RANGES:
        return UNIVERSAL_RATIO_RANGES[ratio_name]
    return None


__all__ = [
    'UNIVERSAL_RATIO_RANGES',
    'MARKET_RATIO_RANGES',
    'PROPORTION_NORMS',
    'SCALE_ANOMALY_THRESHOLD',
    'SCALE_LOW_CONFIDENCE_CUTOFF',
    'get_ratio_range',
]
