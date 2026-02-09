# Path: verification/engine/scoring/constants.py
"""
Scoring Constants for Verification Module

Thresholds, weights, and penalties for quality scoring.
All values can be overridden via .env configuration.
"""

# ==============================================================================
# QUALITY LEVEL THRESHOLDS
# ==============================================================================
# Default thresholds (can be overridden by VERIFICATION_* env vars)

DEFAULT_EXCELLENT_THRESHOLD = 90  # 90-100: Ready for analysis
DEFAULT_GOOD_THRESHOLD = 75       # 75-89: Usable with caution
DEFAULT_FAIR_THRESHOLD = 50       # 50-74: Limited analysis value
DEFAULT_POOR_THRESHOLD = 25       # 25-49: Use at own risk
                                  # 0-24: UNUSABLE

# ==============================================================================
# SCORE WEIGHTS
# ==============================================================================
# How much each check category contributes to overall score

DEFAULT_HORIZONTAL_WEIGHT = 0.40  # Within-statement checks
DEFAULT_VERTICAL_WEIGHT = 0.40    # Cross-statement checks
DEFAULT_LIBRARY_WEIGHT = 0.20     # Standard taxonomy conformance

# ==============================================================================
# SEVERITY PENALTIES
# ==============================================================================
# Points deducted from 100 for each issue by severity

CRITICAL_PENALTY = 25.0   # Major calculation/consistency errors
WARNING_PENALTY = 5.0     # Notable discrepancies
INFO_PENALTY = 0.5        # Minor observations

# ==============================================================================
# CHECK-SPECIFIC WEIGHTS
# ==============================================================================
# Within horizontal checks, how much each contributes

HORIZONTAL_WEIGHTS = {
    'calculation_consistency': 0.50,  # Most important - math must work
    'total_reconciliation': 0.30,     # Totals should match components
    'sign_convention': 0.15,          # Consistent debit/credit
    'duplicate_facts': 0.05,          # Should not have duplicates
}

# Within vertical checks, how much each contributes
# NOTE: xbrl_calculation checks are AGGREGATE checks (many results)
# and use pass-rate scoring instead of accumulated penalties
VERTICAL_WEIGHTS = {
    # New XBRL-sourced calculation checks (aggregate scoring)
    'xbrl_calculation_company': 0.40,   # Company XBRL calculation linkbase
    'xbrl_calculation_taxonomy': 0.30,  # Standard taxonomy calculations
    # Legacy pattern-based checks (for backwards compatibility)
    'balance_sheet_equation': 0.10,     # A = L + E
    'income_statement_linkage': 0.08,   # Net income flows through
    'cash_flow_linkage': 0.05,          # Cash ties to balance sheet
    'retained_earnings_rollforward': 0.02,
    'common_values_consistency': 0.05,
}

# Checks that use aggregate scoring (pass-rate based instead of penalty accumulation)
# These checks can produce many results and should be scored by overall pass rate
AGGREGATE_CHECKS = {
    'xbrl_calculation_company',
    'xbrl_calculation_taxonomy',
}

# Within library checks, how much each contributes
LIBRARY_WEIGHTS = {
    'concept_validity': 0.40,         # Concepts exist in taxonomy
    'period_type_match': 0.25,        # Instant vs duration
    'balance_type_match': 0.20,       # Debit vs credit
    'data_type_match': 0.15,          # Monetary, string, etc.
}

# ==============================================================================
# SCORING BOUNDS
# ==============================================================================

SCORE_MIN = 0.0
SCORE_MAX = 100.0

# Minimum score to be considered "valid" for analysis
MINIMUM_USABLE_SCORE = 25.0

# ==============================================================================
# SCORE DESCRIPTIONS
# ==============================================================================

QUALITY_DESCRIPTIONS = {
    'EXCELLENT': 'Fully consistent, ready for financial analysis',
    'GOOD': 'Minor issues, usable with standard caution',
    'FAIR': 'Notable issues, limited analysis value',
    'POOR': 'Significant issues, use at own risk',
    'UNUSABLE': 'Major inconsistencies, not recommended for analysis',
}

# ==============================================================================
# RECOMMENDATIONS BY QUALITY LEVEL
# ==============================================================================

QUALITY_RECOMMENDATIONS = {
    'EXCELLENT': 'Filing is suitable for comprehensive financial analysis.',
    'GOOD': 'Filing is suitable for analysis. Review flagged warnings.',
    'FAIR': 'Use with caution. Manual verification of key figures recommended.',
    'POOR': 'Significant issues detected. Consider alternative data sources.',
    'UNUSABLE': 'Do not use for analysis. Data integrity compromised.',
}


__all__ = [
    # Thresholds
    'DEFAULT_EXCELLENT_THRESHOLD',
    'DEFAULT_GOOD_THRESHOLD',
    'DEFAULT_FAIR_THRESHOLD',
    'DEFAULT_POOR_THRESHOLD',

    # Weights
    'DEFAULT_HORIZONTAL_WEIGHT',
    'DEFAULT_VERTICAL_WEIGHT',
    'DEFAULT_LIBRARY_WEIGHT',

    # Penalties
    'CRITICAL_PENALTY',
    'WARNING_PENALTY',
    'INFO_PENALTY',

    # Check-specific weights
    'HORIZONTAL_WEIGHTS',
    'VERTICAL_WEIGHTS',
    'LIBRARY_WEIGHTS',
    'AGGREGATE_CHECKS',

    # Bounds
    'SCORE_MIN',
    'SCORE_MAX',
    'MINIMUM_USABLE_SCORE',

    # Descriptions
    'QUALITY_DESCRIPTIONS',
    'QUALITY_RECOMMENDATIONS',
]
