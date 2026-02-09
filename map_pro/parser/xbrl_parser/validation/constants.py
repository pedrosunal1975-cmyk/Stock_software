# Path: xbrl_parser/validation/constants.py
"""
Validation Module Constants

Central repository for all validation-related constants, thresholds, and patterns.

NO HARDCODED market names, URLs, or addresses should exist in other validation
module files - all constants should be imported from this file.
"""

# ==============================================================================
# VALIDATION LEVELS
# ==============================================================================

# Validation level options
VALIDATION_LEVEL_NONE = "none"
VALIDATION_LEVEL_BASIC = "basic"
VALIDATION_LEVEL_FULL = "full"

VALIDATION_LEVELS = [
    VALIDATION_LEVEL_NONE,
    VALIDATION_LEVEL_BASIC,
    VALIDATION_LEVEL_FULL
]

# ==============================================================================
# CALCULATION VALIDATION
# ==============================================================================

# Default calculation tolerance (1%)
DEFAULT_CALCULATION_TOLERANCE = 0.01

# Minimum tolerance threshold
MIN_CALCULATION_TOLERANCE = 0.0

# Maximum tolerance threshold
MAX_CALCULATION_TOLERANCE = 1.0

# Decimal precision for tolerance calculations
TOLERANCE_DECIMAL_PRECISION = 10

# Infinite precision indicator
INFINITE_PRECISION = "INF"

# ==============================================================================
# STRUCTURAL VALIDATION
# ==============================================================================

# Maximum allowed contexts per filing
MAX_CONTEXTS_WARNING_THRESHOLD = 5000
MAX_CONTEXTS_ERROR_THRESHOLD = 10000

# Maximum allowed units per filing
MAX_UNITS_WARNING_THRESHOLD = 500
MAX_UNITS_ERROR_THRESHOLD = 1000

# Maximum allowed facts per filing
MAX_FACTS_WARNING_THRESHOLD = 50000
MAX_FACTS_ERROR_THRESHOLD = 100000

# Maximum dimension depth
MAX_DIMENSION_DEPTH = 10

# Required attributes for facts
REQUIRED_FACT_ATTRIBUTES = ['contextRef']
REQUIRED_NUMERIC_FACT_ATTRIBUTES = ['contextRef', 'unitRef']

# ==============================================================================
# DIMENSIONAL VALIDATION
# ==============================================================================

# Maximum members per dimension
MAX_DIMENSION_MEMBERS = 1000

# Maximum dimensions per hypercube
MAX_DIMENSIONS_PER_HYPERCUBE = 20

# Dimension types
DIMENSION_TYPE_EXPLICIT = "explicit"
DIMENSION_TYPE_TYPED = "typed"

# ==============================================================================
# COMPLETENESS VALIDATION
# ==============================================================================

# Orphan detection thresholds
MAX_ORPHAN_CONTEXTS_PERCENT = 10  # Warning if >10% contexts unused
MAX_ORPHAN_UNITS_PERCENT = 10     # Warning if >10% units unused

# Coverage thresholds
MIN_COVERAGE_PERCENT = 95  # Warning if <95% elements parsed

# ==============================================================================
# ERROR SEVERITY THRESHOLDS
# ==============================================================================

# Maximum errors before marking filing as FAILED
MAX_CRITICAL_ERRORS = 10
MAX_ERRORS = 100
MAX_WARNINGS = 1000

# ==============================================================================
# VALIDATION ERROR CODES
# ==============================================================================

# NOTE: Error codes should be stored in ParsingError.details field, not as a 
# separate 'code' parameter (which doesn't exist in the model).
#
# Example usage:
#   error = ParsingError(
#       category=ErrorCategory.XBRL_INVALID,
#       severity=ErrorSeverity.ERROR,
#       message=MSG_MISSING_CONTEXT,
#       details=ERR_MISSING_CONTEXT  # <- Error code goes here
#   )

# Structural validation error codes
ERR_MISSING_CONTEXT = "VAL001"
ERR_MISSING_UNIT = "VAL002"
ERR_INVALID_CONTEXT_REF = "VAL003"
ERR_INVALID_UNIT_REF = "VAL004"
ERR_INVALID_DIMENSION_REF = "VAL005"
ERR_INVALID_MEMBER_REF = "VAL006"
ERR_MISSING_REQUIRED_ATTRIBUTE = "VAL007"
ERR_MUTUALLY_EXCLUSIVE_ATTRIBUTES = "VAL008"
ERR_INVALID_PERIOD = "VAL009"
ERR_INVALID_DATE_FORMAT = "VAL010"

# Calculation validation error codes
ERR_CALCULATION_INCONSISTENT = "VAL101"
ERR_CALCULATION_MISSING_FACT = "VAL102"
ERR_CALCULATION_CONTEXT_MISMATCH = "VAL103"
ERR_CALCULATION_TOLERANCE_EXCEEDED = "VAL104"
ERR_CALCULATION_INVALID_WEIGHT = "VAL105"

# Dimensional validation error codes
ERR_DIMENSION_NOT_IN_HYPERCUBE = "VAL201"
ERR_REQUIRED_DIMENSION_MISSING = "VAL202"
ERR_CLOSED_DIMENSION_INVALID_MEMBER = "VAL203"
ERR_TYPED_DIMENSION_INVALID_XML = "VAL204"
ERR_DIMENSION_DEPTH_EXCEEDED = "VAL205"

# Completeness validation error codes
ERR_ORPHAN_CONTEXT = "VAL301"
ERR_ORPHAN_UNIT = "VAL302"
ERR_MISSING_ELEMENT = "VAL303"
ERR_COVERAGE_INSUFFICIENT = "VAL304"

# XBRL specification error codes
ERR_XBRL_SPEC_VIOLATION = "VAL401"
ERR_SCHEMA_VALIDATION_FAILED = "VAL402"
ERR_LINKBASE_VALIDATION_FAILED = "VAL403"

# ==============================================================================
# VALIDATION MESSAGES
# ==============================================================================

# Structural validation messages
MSG_MISSING_CONTEXT = "Fact references non-existent context"
MSG_MISSING_UNIT = "Numeric fact references non-existent unit"
MSG_INVALID_CONTEXT_REF = "Invalid context reference"
MSG_INVALID_UNIT_REF = "Invalid unit reference"
MSG_INVALID_DIMENSION_REF = "Dimension does not exist in taxonomy"
MSG_INVALID_MEMBER_REF = "Member does not exist in domain"
MSG_MISSING_REQUIRED_ATTRIBUTE = "Required attribute is missing"
MSG_MUTUALLY_EXCLUSIVE_ATTRIBUTES = "Mutually exclusive attributes present"
MSG_INVALID_PERIOD = "Period dates are invalid or illogical"
MSG_INVALID_DATE_FORMAT = "Date format does not conform to ISO 8601"

# Calculation validation messages
MSG_CALCULATION_INCONSISTENT = "Calculation relationship does not balance"
MSG_CALCULATION_MISSING_FACT = "Calculation requires missing fact"
MSG_CALCULATION_CONTEXT_MISMATCH = "Facts in calculation have different contexts"
MSG_CALCULATION_TOLERANCE_EXCEEDED = "Calculation difference exceeds tolerance"
MSG_CALCULATION_INVALID_WEIGHT = "Calculation weight is invalid"

# Dimensional validation messages
MSG_DIMENSION_NOT_IN_HYPERCUBE = "Dimension not defined in hypercube"
MSG_REQUIRED_DIMENSION_MISSING = "Required dimension is missing"
MSG_CLOSED_DIMENSION_INVALID_MEMBER = "Member not allowed for closed dimension"
MSG_TYPED_DIMENSION_INVALID_XML = "Typed dimension contains invalid XML"
MSG_DIMENSION_DEPTH_EXCEEDED = "Dimension depth exceeds maximum"

# Completeness validation messages
MSG_ORPHAN_CONTEXT = "Orphan contexts detected - not referenced by any facts"
MSG_ORPHAN_UNIT = "Orphan units detected - not referenced by any facts"
MSG_MISSING_ELEMENT = "Expected element was not parsed"
MSG_COVERAGE_INSUFFICIENT = "Coverage percentage is below threshold"

# XBRL specification messages
MSG_XBRL_SPEC_VIOLATION = "XBRL specification violation detected"
MSG_SCHEMA_VALIDATION_FAILED = "Schema validation failed"
MSG_LINKBASE_VALIDATION_FAILED = "Linkbase validation failed"

# ==============================================================================
# VALIDATION CATEGORIES
# ==============================================================================

# Validation category identifiers
CATEGORY_STRUCTURAL = "structural"
CATEGORY_CALCULATION = "calculation"
CATEGORY_DIMENSIONAL = "dimensional"
CATEGORY_COMPLETENESS = "completeness"
CATEGORY_SPECIFICATION = "specification"

VALIDATION_CATEGORIES = [
    CATEGORY_STRUCTURAL,
    CATEGORY_CALCULATION,
    CATEGORY_DIMENSIONAL,
    CATEGORY_COMPLETENESS,
    CATEGORY_SPECIFICATION
]

# ==============================================================================
# VALIDATOR IDENTIFIERS
# ==============================================================================

# Validator names
VALIDATOR_STRUCTURAL = "structural_validator"
VALIDATOR_CALCULATION = "calculation_validator"
VALIDATOR_DIMENSIONAL = "dimensional_validator"
VALIDATOR_COMPLETENESS = "completeness_validator"

# ==============================================================================
# VALIDATION RESULT STATUS
# ==============================================================================

# Validation result status values
STATUS_PASSED = "passed"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

# ==============================================================================
# REPORT FORMATS
# ==============================================================================

# Report output formats
REPORT_FORMAT_TEXT = "text"
REPORT_FORMAT_JSON = "json"
REPORT_FORMAT_HTML = "html"


__all__ = [
    # Validation levels
    'VALIDATION_LEVEL_NONE',
    'VALIDATION_LEVEL_BASIC',
    'VALIDATION_LEVEL_FULL',
    'VALIDATION_LEVELS',
    
    # Calculation constants
    'DEFAULT_CALCULATION_TOLERANCE',
    'MIN_CALCULATION_TOLERANCE',
    'MAX_CALCULATION_TOLERANCE',
    'TOLERANCE_DECIMAL_PRECISION',
    'INFINITE_PRECISION',
    
    # Structural thresholds
    'MAX_CONTEXTS_WARNING_THRESHOLD',
    'MAX_CONTEXTS_ERROR_THRESHOLD',
    'MAX_UNITS_WARNING_THRESHOLD',
    'MAX_UNITS_ERROR_THRESHOLD',
    'MAX_FACTS_WARNING_THRESHOLD',
    'MAX_FACTS_ERROR_THRESHOLD',
    'MAX_DIMENSION_DEPTH',
    'REQUIRED_FACT_ATTRIBUTES',
    'REQUIRED_NUMERIC_FACT_ATTRIBUTES',
    
    # Dimensional constants
    'MAX_DIMENSION_MEMBERS',
    'MAX_DIMENSIONS_PER_HYPERCUBE',
    'DIMENSION_TYPE_EXPLICIT',
    'DIMENSION_TYPE_TYPED',
    
    # Completeness thresholds
    'MAX_ORPHAN_CONTEXTS_PERCENT',
    'MAX_ORPHAN_UNITS_PERCENT',
    'MIN_COVERAGE_PERCENT',
    
    # Error thresholds
    'MAX_CRITICAL_ERRORS',
    'MAX_ERRORS',
    'MAX_WARNINGS',
    
    # Error codes
    'ERR_MISSING_CONTEXT',
    'ERR_MISSING_UNIT',
    'ERR_INVALID_CONTEXT_REF',
    'ERR_INVALID_UNIT_REF',
    'ERR_INVALID_DIMENSION_REF',
    'ERR_INVALID_MEMBER_REF',
    'ERR_MISSING_REQUIRED_ATTRIBUTE',
    'ERR_MUTUALLY_EXCLUSIVE_ATTRIBUTES',
    'ERR_INVALID_PERIOD',
    'ERR_INVALID_DATE_FORMAT',
    'ERR_CALCULATION_INCONSISTENT',
    'ERR_CALCULATION_MISSING_FACT',
    'ERR_CALCULATION_CONTEXT_MISMATCH',
    'ERR_CALCULATION_TOLERANCE_EXCEEDED',
    'ERR_CALCULATION_INVALID_WEIGHT',
    'ERR_DIMENSION_NOT_IN_HYPERCUBE',
    'ERR_REQUIRED_DIMENSION_MISSING',
    'ERR_CLOSED_DIMENSION_INVALID_MEMBER',
    'ERR_TYPED_DIMENSION_INVALID_XML',
    'ERR_DIMENSION_DEPTH_EXCEEDED',
    'ERR_ORPHAN_CONTEXT',
    'ERR_ORPHAN_UNIT',
    'ERR_MISSING_ELEMENT',
    'ERR_COVERAGE_INSUFFICIENT',
    'ERR_XBRL_SPEC_VIOLATION',
    'ERR_SCHEMA_VALIDATION_FAILED',
    'ERR_LINKBASE_VALIDATION_FAILED',
    
    # Messages
    'MSG_MISSING_CONTEXT',
    'MSG_MISSING_UNIT',
    'MSG_INVALID_CONTEXT_REF',
    'MSG_INVALID_UNIT_REF',
    'MSG_INVALID_DIMENSION_REF',
    'MSG_INVALID_MEMBER_REF',
    'MSG_MISSING_REQUIRED_ATTRIBUTE',
    'MSG_MUTUALLY_EXCLUSIVE_ATTRIBUTES',
    'MSG_INVALID_PERIOD',
    'MSG_INVALID_DATE_FORMAT',
    'MSG_CALCULATION_INCONSISTENT',
    'MSG_CALCULATION_MISSING_FACT',
    'MSG_CALCULATION_CONTEXT_MISMATCH',
    'MSG_CALCULATION_TOLERANCE_EXCEEDED',
    'MSG_CALCULATION_INVALID_WEIGHT',
    'MSG_DIMENSION_NOT_IN_HYPERCUBE',
    'MSG_REQUIRED_DIMENSION_MISSING',
    'MSG_CLOSED_DIMENSION_INVALID_MEMBER',
    'MSG_TYPED_DIMENSION_INVALID_XML',
    'MSG_DIMENSION_DEPTH_EXCEEDED',
    'MSG_ORPHAN_CONTEXT',
    'MSG_ORPHAN_UNIT',
    'MSG_MISSING_ELEMENT',
    'MSG_COVERAGE_INSUFFICIENT',
    'MSG_XBRL_SPEC_VIOLATION',
    'MSG_SCHEMA_VALIDATION_FAILED',
    'MSG_LINKBASE_VALIDATION_FAILED',
    
    # Categories
    'CATEGORY_STRUCTURAL',
    'CATEGORY_CALCULATION',
    'CATEGORY_DIMENSIONAL',
    'CATEGORY_COMPLETENESS',
    'CATEGORY_SPECIFICATION',
    'VALIDATION_CATEGORIES',
    
    # Validators
    'VALIDATOR_STRUCTURAL',
    'VALIDATOR_CALCULATION',
    'VALIDATOR_DIMENSIONAL',
    'VALIDATOR_COMPLETENESS',
    
    # Status
    'STATUS_PASSED',
    'STATUS_FAILED',
    'STATUS_SKIPPED',
    
    # Formats
    'REPORT_FORMAT_TEXT',
    'REPORT_FORMAT_JSON',
    'REPORT_FORMAT_HTML',
]