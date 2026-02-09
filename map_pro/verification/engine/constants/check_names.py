# Path: verification/engine/checks_v2/constants/check_names.py
"""
Check Name Constants for XBRL Verification

Standard identifiers for verification checks.
Used for result reporting, logging, and check selection.

Categories:
1. Horizontal Checks - Within a single statement (calculation linkbase)
2. Vertical Checks - Across statements (cross-statement consistency)
3. Library Checks - Against standard taxonomy
"""

# ==============================================================================
# HORIZONTAL CHECK NAMES
# ==============================================================================
# Checks within a single statement using XBRL calculation linkbase.
# These verify that calculations defined by the company are internally consistent.

# Calculation consistency - parent = sum(children * weights)
CHECK_CALCULATION_CONSISTENCY = 'calculation_consistency'

# Total reconciliation - totals match expected sums
CHECK_TOTAL_RECONCILIATION = 'total_reconciliation'

# Sign convention - values have correct signs per XBRL convention
CHECK_SIGN_CONVENTION = 'sign_convention'

# Duplicate facts - detecting and handling duplicate fact entries
CHECK_DUPLICATE_FACTS = 'duplicate_facts'

# All horizontal check names
HORIZONTAL_CHECK_NAMES = [
    CHECK_CALCULATION_CONSISTENCY,
    CHECK_TOTAL_RECONCILIATION,
    CHECK_SIGN_CONVENTION,
    CHECK_DUPLICATE_FACTS,
]


# ==============================================================================
# VERTICAL CHECK NAMES
# ==============================================================================
# Checks across statements and contexts.
# These verify consistency between different financial statements and periods.

# Cross-statement consistency - same concept has same value across statements
# when reported in the same period but different contexts
CHECK_CROSS_STATEMENT_CONSISTENCY = 'cross_statement_consistency'

# Period value consistency - values match across contexts for same period
CHECK_PERIOD_VALUE_CONSISTENCY = 'period_value_consistency'

# All vertical check names
VERTICAL_CHECK_NAMES = [
    CHECK_CROSS_STATEMENT_CONSISTENCY,
    CHECK_PERIOD_VALUE_CONSISTENCY,
]


# ==============================================================================
# ALL CHECK NAMES
# ==============================================================================
# Complete list of all check names for iteration

ALL_CHECK_NAMES = HORIZONTAL_CHECK_NAMES + VERTICAL_CHECK_NAMES


__all__ = [
    # Horizontal checks
    'CHECK_CALCULATION_CONSISTENCY',
    'CHECK_TOTAL_RECONCILIATION',
    'CHECK_SIGN_CONVENTION',
    'CHECK_DUPLICATE_FACTS',
    'HORIZONTAL_CHECK_NAMES',
    # Vertical checks
    'CHECK_CROSS_STATEMENT_CONSISTENCY',
    'CHECK_PERIOD_VALUE_CONSISTENCY',
    'VERTICAL_CHECK_NAMES',
    # All checks
    'ALL_CHECK_NAMES',
]
