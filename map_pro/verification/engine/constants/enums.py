# Path: verification/engine/checks_v2/constants/enums.py
"""
Enumeration Constants for XBRL Verification

Type-safe enumerations for classification and status tracking.
Using enums instead of string literals prevents typos and enables
IDE autocompletion.

Categories:
1. PeriodType - Duration vs Instant periods
2. DuplicateType - Complete, Consistent, Inconsistent duplicates
3. MatchType - How facts were matched (exact, fallback, etc.)
4. BindingStatus - Why calculations bind or skip
"""

from enum import Enum


# ==============================================================================
# PERIOD TYPE
# ==============================================================================

class PeriodType(Enum):
    """
    XBRL period types.

    Duration: Period of time (e.g., year ended Dec 31, 2024)
    Instant: Point in time (e.g., as of Dec 31, 2024)
    Unknown: Period type could not be determined
    """
    DURATION = 'duration'
    INSTANT = 'instant'
    UNKNOWN = 'unknown'


# ==============================================================================
# DUPLICATE TYPE
# ==============================================================================

class DuplicateType(Enum):
    """
    Types of duplicate facts per XBRL Duplicates Guidance.

    COMPLETE: Same value, same precision - ignore, use one
    CONSISTENT: Same value (within tolerance), different precision - use most precise
    INCONSISTENT: Different values - error, cannot use in calculations
    """
    COMPLETE = "complete"
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"


# ==============================================================================
# MATCH TYPE
# ==============================================================================

class MatchType(Enum):
    """
    How a fact was matched during verification.

    EXACT: Same context_id (strict C-Equal)
    FALLBACK: Different context, but compatible period
    PERIOD_MATCH: Matched by period key
    DIMENSIONAL: Matched via dimensional fallback
    NONE: No match found
    """
    EXACT = 'exact'
    FALLBACK = 'fallback'
    PERIOD_MATCH = 'period_match'
    DIMENSIONAL = 'dimensional'
    NONE = 'none'


# ==============================================================================
# BINDING STATUS
# ==============================================================================

class BindingStatus(Enum):
    """
    Status of calculation binding attempt.

    Calculations are SKIPPED (not failed) when binding conditions are not met.
    This is a critical distinction:
    - SKIP: Cannot verify because data is incomplete or invalid
    - BINDS: Can proceed with verification

    After binding, verification determines PASS or FAIL.
    """
    BINDS = "binds"                           # Can verify this calculation
    SKIP_NO_PARENT = "skip_no_parent"         # Parent not found in context
    SKIP_NO_CHILDREN = "skip_no_children"     # No children found in context
    SKIP_INCOMPLETE = "skip_incomplete"       # Too few children found (below threshold)
    SKIP_INCONSISTENT_PARENT = "skip_inconsistent_parent"  # Parent has inconsistent duplicates
    SKIP_INCONSISTENT_CHILD = "skip_inconsistent_child"    # A child has inconsistent duplicates
    SKIP_UNIT_MISMATCH = "skip_unit_mismatch"  # Units don't match (not u-equal)
    SKIP_DIMENSIONAL = "skip_dimensional"      # Skipped due to dimensional context rules


# ==============================================================================
# CHECK RESULT SEVERITY
# ==============================================================================

class Severity(Enum):
    """
    Severity levels for check results.

    CRITICAL: Significant issue that affects data reliability
    WARNING: Potential issue that should be reviewed
    INFO: Informational note, not necessarily a problem
    PASS: Check passed successfully
    SKIP: Check was skipped (binding conditions not met)
    """
    CRITICAL = 'critical'
    WARNING = 'warning'
    INFO = 'info'
    PASS = 'pass'
    SKIP = 'skip'


# ==============================================================================
# SIGN SOURCE
# ==============================================================================

class SignSource(Enum):
    """
    Source of sign correction information.

    Tracks where sign correction came from for diagnostic purposes.
    """
    XBRL_ATTRIBUTE = "xbrl_sign_attribute"    # sign="-" in iXBRL
    CALCULATION_WEIGHT = "calculation_weight"  # weight attribute in cal linkbase
    CONCEPT_SEMANTICS = "concept_semantics"    # Inferred from concept name
    VALUE_PATTERN = "value_pattern"            # Detected from value patterns
    PERIOD_FALLBACK = "period_fallback"        # Matched by period (different context hash)
    NONE = "none"


# ==============================================================================
# DUPLICATE SOURCE
# ==============================================================================

class DuplicateSource(Enum):
    """
    Likely source/reason for duplicate facts.

    Helps diagnose WHY duplicates exist, which informs how to handle them.
    This is a heuristic classification - not always 100% accurate.
    """
    IXBRL_DISPLAY = "ixbrl_display"        # Same fact shown multiple times in iXBRL
    PRECISION_VARIANT = "precision_variant"  # Same value at different precision levels
    RESTATEMENT = "restatement"             # Original vs restated values
    ROUNDING_DIFF = "rounding_diff"         # Values differ only by rounding
    VALUE_CONFLICT = "value_conflict"       # Genuinely different values (error)
    UNKNOWN = "unknown"                      # Could not determine source


__all__ = [
    'PeriodType',
    'DuplicateType',
    'MatchType',
    'BindingStatus',
    'Severity',
    'SignSource',
    'DuplicateSource',
]
