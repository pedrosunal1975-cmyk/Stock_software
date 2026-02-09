# Path: verification/engine/checks_v2/constants/tolerances.py
"""
Numeric Tolerances and Thresholds for XBRL Verification

All numeric configuration values in one place.
These values control calculation comparisons, duplicate detection,
and display limits throughout the verification process.

Categories:
1. Calculation Tolerances - For comparing calculated vs reported values
2. Sign Handling Tolerances - For detecting sign pattern issues
3. Duplicate Detection Tolerances - For classifying duplicate facts
4. Decimal Comparison - For XBRL banker's rounding
5. Display Limits - For diagnostic output and logging
"""

# ==============================================================================
# CALCULATION TOLERANCES
# ==============================================================================

# Percentage tolerance for calculation comparisons
# When sum of children differs from parent by less than this percentage,
# the calculation is considered valid.
# Example: 1% means a $1,000,000 parent can differ by up to $10,000 from sum
DEFAULT_CALCULATION_TOLERANCE = 0.01  # 1%

# Absolute rounding tolerance for small values
# For values below LARGE_VALUE_THRESHOLD, this absolute difference is allowed.
# Handles cases where $1 differences due to rounding are not meaningful.
DEFAULT_ROUNDING_TOLERANCE = 1.0  # $1 or equivalent unit

# Threshold distinguishing small from large values
# Below this: use absolute tolerance (DEFAULT_ROUNDING_TOLERANCE)
# Above this: use percentage tolerance (DEFAULT_CALCULATION_TOLERANCE)
LARGE_VALUE_THRESHOLD = 1000.0

# Minimum percentage of children required for calculation to bind
# If fewer than this percentage of children are found, the calculation
# is SKIPPED (not failed) because incomplete data cannot verify.
# Example: 0.5 means at least 50% of children must be found
CALCULATION_COMPLETENESS_THRESHOLD = 0.5  # 50% minimum

# Overshoot severity threshold
# When sum of children exceeds parent, if excess is less than this percentage
# of parent magnitude, treat as rounding issue (WARNING) not real problem (CRITICAL).
# Example: 0.05 means overshoot up to 5% of parent value is considered rounding
OVERSHOOT_ROUNDING_THRESHOLD = 0.05  # 5%


# ==============================================================================
# VERTICAL CHECK TOLERANCES
# ==============================================================================

# Tolerance for cross-statement value consistency
# When the same concept appears in multiple contexts for the same period,
# values within this tolerance are considered consistent.
CROSS_STATEMENT_TOLERANCE = 0.01  # 1%

# Minimum number of contexts with same concept/period for vertical check
# If fewer contexts, skip the check (not enough data to verify)
MIN_CROSS_STATEMENT_CONTEXTS = 2


# ==============================================================================
# SIGN HANDLING TOLERANCES
# ==============================================================================

# Tolerance for detecting sign pattern issues
# Used to check if values match in magnitude but differ in sign
# (abs(value1) - abs(value2)) / max(abs(value1), abs(value2)) < tolerance
SIGN_MAGNITUDE_TOLERANCE = 0.01  # 1%

# Tolerance for detecting doubling pattern
# When difference is approximately 2x the expected sum, indicates
# parent sign is opposite of expected (common in cash flow statements)
SIGN_DOUBLING_TOLERANCE = 0.01  # 1%


# ==============================================================================
# DUPLICATE DETECTION TOLERANCES
# ==============================================================================

# Percentage tolerance for duplicate detection fallback
# When decimal tolerance comparison doesn't work (e.g., missing decimals),
# values within this percentage difference are considered duplicates.
# Example: 0.02 means values differing by less than 2% are treated as duplicates
DUPLICATE_PERCENTAGE_TOLERANCE = 0.02  # 2%


# ==============================================================================
# DECIMAL COMPARISON TOLERANCES
# ==============================================================================

# Epsilon for floating point comparison when decimals is None
# Used as a small tolerance to account for floating point arithmetic
# when no precision information is available.
DECIMAL_COMPARISON_EPSILON_BASE = 0.5

# Multiplier for epsilon calculation when decimals is specified
# epsilon = 10 ** (-decimals) * EPSILON_MULTIPLIER
# Example: decimals=2 gives epsilon = 0.01 * 0.5 = 0.005
DECIMAL_EPSILON_MULTIPLIER = 0.5


# ==============================================================================
# DISPLAY AND DIAGNOSTIC LIMITS
# ==============================================================================

# Number of sample concepts to include in diagnostic summaries
# Helps identify normalization issues without overwhelming output
SAMPLE_CONCEPTS_LIMIT = 50

# Number of sample contexts to include in diagnostic summaries
SAMPLE_CONTEXTS_LIMIT = 10

# Maximum number of missing children to display in detailed messages
# Prevents log bloat while still showing useful diagnostic info
MAX_MISSING_CHILDREN_DISPLAY = 5

# Maximum duplicates to display in duplicate check results
MAX_DUPLICATES_DISPLAY = 20

# Maximum inconsistent duplicates to display in inline results
MAX_INCONSISTENT_DUPLICATES_DISPLAY = 20

# Minimum multi-role parents count to trigger info log message
MAX_MULTI_ROLE_PARENTS_LOG = 1


# ==============================================================================
# SCORING CONSTANTS
# ==============================================================================

# Penalty percentage for critical issues as portion of total checks
# Applied as: (critical_count / total_checks) * CRITICAL_PENALTY_WEIGHT
CRITICAL_PENALTY_WEIGHT = 50

# Penalty percentage for warning issues as portion of total checks
# Applied as: (warning_count / total_checks) * WARNING_PENALTY_WEIGHT
WARNING_PENALTY_WEIGHT = 20

# Minimum possible score (floor)
MIN_SCORE = 0.0

# Maximum possible score (ceiling)
MAX_SCORE = 100.0

# Default score when no checks exist
DEFAULT_NO_CHECKS_SCORE = 100.0

# Score multiplier for converting pass rate to percentage
SCORE_PERCENTAGE_MULTIPLIER = 100


# ==============================================================================
# COMPARISON AND ITERATION CONSTANTS
# ==============================================================================

# Threshold for considering a value as zero in comparisons
ZERO_THRESHOLD = 0

# Return value for nil/zero value parsing
NIL_VALUE_RETURN = 0.0

# Initial value for expected sum calculations
INITIAL_EXPECTED_SUM = 0.0

# Default overshoot ratio when parent magnitude is zero (division by zero case)
DEFAULT_OVERSHOOT_RATIO = 1.0

# Minimum number of entries to be considered a duplicate set
MIN_DUPLICATE_ENTRIES = 1

# Starting index for iterating over entries after the first
ITERATION_START_INDEX = 1

# Index for accessing first element in arrays
FIRST_ELEMENT_INDEX = 0


__all__ = [
    # Calculation tolerances
    'DEFAULT_CALCULATION_TOLERANCE',
    'DEFAULT_ROUNDING_TOLERANCE',
    'LARGE_VALUE_THRESHOLD',
    'CALCULATION_COMPLETENESS_THRESHOLD',
    'OVERSHOOT_ROUNDING_THRESHOLD',
    # Vertical check tolerances
    'CROSS_STATEMENT_TOLERANCE',
    'MIN_CROSS_STATEMENT_CONTEXTS',
    # Sign handling tolerances
    'SIGN_MAGNITUDE_TOLERANCE',
    'SIGN_DOUBLING_TOLERANCE',
    # Duplicate tolerances
    'DUPLICATE_PERCENTAGE_TOLERANCE',
    # Decimal tolerances
    'DECIMAL_COMPARISON_EPSILON_BASE',
    'DECIMAL_EPSILON_MULTIPLIER',
    # Display limits
    'SAMPLE_CONCEPTS_LIMIT',
    'SAMPLE_CONTEXTS_LIMIT',
    'MAX_MISSING_CHILDREN_DISPLAY',
    'MAX_DUPLICATES_DISPLAY',
    'MAX_INCONSISTENT_DUPLICATES_DISPLAY',
    'MAX_MULTI_ROLE_PARENTS_LOG',
    # Scoring constants
    'CRITICAL_PENALTY_WEIGHT',
    'WARNING_PENALTY_WEIGHT',
    'MIN_SCORE',
    'MAX_SCORE',
    'DEFAULT_NO_CHECKS_SCORE',
    'SCORE_PERCENTAGE_MULTIPLIER',
    # Comparison constants
    'ZERO_THRESHOLD',
    'NIL_VALUE_RETURN',
    'INITIAL_EXPECTED_SUM',
    'DEFAULT_OVERSHOOT_RATIO',
    'MIN_DUPLICATE_ENTRIES',
    'ITERATION_START_INDEX',
    'FIRST_ELEMENT_INDEX',
]
