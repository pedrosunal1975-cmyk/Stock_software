# Path: verification/engine/checks_v2/constants/__init__.py
"""
Verification Constants Module

All configuration values, thresholds, patterns, and constants for verification.
This module eliminates hardcoded values from processing files.

Categories:
- tolerances: Numeric thresholds for calculations and comparisons
- patterns: Regex patterns for period, date, context, name extraction
- xbrl: XBRL specification constants (namespaces, arcroles)
- naming: Name normalization separators and prefixes
- check_names: Standard check identifiers
"""

from .tolerances import (
    # Calculation tolerances
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    LARGE_VALUE_THRESHOLD,
    CALCULATION_COMPLETENESS_THRESHOLD,
    OVERSHOOT_ROUNDING_THRESHOLD,
    # Vertical check tolerances
    CROSS_STATEMENT_TOLERANCE,
    MIN_CROSS_STATEMENT_CONTEXTS,
    # Sign handling tolerances
    SIGN_MAGNITUDE_TOLERANCE,
    SIGN_DOUBLING_TOLERANCE,
    # Duplicate tolerances
    DUPLICATE_PERCENTAGE_TOLERANCE,
    # Decimal tolerances
    DECIMAL_COMPARISON_EPSILON_BASE,
    DECIMAL_EPSILON_MULTIPLIER,
    # Display limits
    SAMPLE_CONCEPTS_LIMIT,
    SAMPLE_CONTEXTS_LIMIT,
    MAX_MISSING_CHILDREN_DISPLAY,
    MAX_DUPLICATES_DISPLAY,
    MAX_INCONSISTENT_DUPLICATES_DISPLAY,
)

from .patterns import (
    # Period patterns
    PERIOD_TYPE_INDICATORS,
    DATE_COMPONENT_PATTERNS,
    PERIOD_EXTRACTION_PATTERNS,
    CONTEXT_ID_DATE_SEPARATORS,
    REGEX_YEAR_PATTERN,
    # Dimensional patterns
    DIMENSIONAL_CONTEXT_INDICATORS,
    # Value representations
    NIL_VALUES,
    EM_DASH,
    EN_DASH,
)

from .naming import (
    # Concept separators
    CONCEPT_SEPARATORS,
    CANONICAL_SEPARATOR,
    # Taxonomy prefixes
    KNOWN_TAXONOMY_PREFIXES,
    MAX_EXTENSION_PREFIX_LENGTH,
)

from .xbrl import (
    # Namespaces
    XLINK_NAMESPACE,
    XBRL_LINKBASE_NAMESPACE,
    XBRL_INSTANCE_NAMESPACE,
    XBRL_DIMENSIONS_NAMESPACE,
    # Attributes
    XLINK_ATTRS,
    # Linkbase elements
    LINKBASE_ELEMENTS,
    ARC_ATTRIBUTES,
    # Arcroles
    ARCROLE_CALCULATION,
    ARCROLE_SUMMATION_ITEM,
)

from .check_names import (
    # Horizontal checks
    CHECK_CALCULATION_CONSISTENCY,
    CHECK_TOTAL_RECONCILIATION,
    CHECK_SIGN_CONVENTION,
    CHECK_DUPLICATE_FACTS,
    HORIZONTAL_CHECK_NAMES,
    # Vertical checks
    CHECK_CROSS_STATEMENT_CONSISTENCY,
    CHECK_PERIOD_VALUE_CONSISTENCY,
    VERTICAL_CHECK_NAMES,
    # All checks
    ALL_CHECK_NAMES,
)

from .enums import (
    # Period types
    PeriodType,
    # Duplicate types
    DuplicateType,
    # Match types
    MatchType,
    # Binding status
    BindingStatus,
)

__all__ = [
    # Tolerances
    'DEFAULT_CALCULATION_TOLERANCE',
    'DEFAULT_ROUNDING_TOLERANCE',
    'LARGE_VALUE_THRESHOLD',
    'CALCULATION_COMPLETENESS_THRESHOLD',
    'OVERSHOOT_ROUNDING_THRESHOLD',
    'CROSS_STATEMENT_TOLERANCE',
    'MIN_CROSS_STATEMENT_CONTEXTS',
    'SIGN_MAGNITUDE_TOLERANCE',
    'SIGN_DOUBLING_TOLERANCE',
    'DUPLICATE_PERCENTAGE_TOLERANCE',
    'DECIMAL_COMPARISON_EPSILON_BASE',
    'DECIMAL_EPSILON_MULTIPLIER',
    'SAMPLE_CONCEPTS_LIMIT',
    'SAMPLE_CONTEXTS_LIMIT',
    'MAX_MISSING_CHILDREN_DISPLAY',
    'MAX_DUPLICATES_DISPLAY',
    'MAX_INCONSISTENT_DUPLICATES_DISPLAY',
    # Patterns
    'PERIOD_TYPE_INDICATORS',
    'DATE_COMPONENT_PATTERNS',
    'PERIOD_EXTRACTION_PATTERNS',
    'CONTEXT_ID_DATE_SEPARATORS',
    'REGEX_YEAR_PATTERN',
    'DIMENSIONAL_CONTEXT_INDICATORS',
    'NIL_VALUES',
    'EM_DASH',
    'EN_DASH',
    # Naming
    'CONCEPT_SEPARATORS',
    'CANONICAL_SEPARATOR',
    'KNOWN_TAXONOMY_PREFIXES',
    'MAX_EXTENSION_PREFIX_LENGTH',
    # XBRL
    'XLINK_NAMESPACE',
    'XBRL_LINKBASE_NAMESPACE',
    'XBRL_INSTANCE_NAMESPACE',
    'XBRL_DIMENSIONS_NAMESPACE',
    'XLINK_ATTRS',
    'LINKBASE_ELEMENTS',
    'ARC_ATTRIBUTES',
    'ARCROLE_CALCULATION',
    'ARCROLE_SUMMATION_ITEM',
    # Check names
    'CHECK_CALCULATION_CONSISTENCY',
    'CHECK_TOTAL_RECONCILIATION',
    'CHECK_SIGN_CONVENTION',
    'CHECK_DUPLICATE_FACTS',
    'HORIZONTAL_CHECK_NAMES',
    'CHECK_CROSS_STATEMENT_CONSISTENCY',
    'CHECK_PERIOD_VALUE_CONSISTENCY',
    'VERTICAL_CHECK_NAMES',
    'ALL_CHECK_NAMES',
    # Enums
    'PeriodType',
    'DuplicateType',
    'MatchType',
    'BindingStatus',
]
