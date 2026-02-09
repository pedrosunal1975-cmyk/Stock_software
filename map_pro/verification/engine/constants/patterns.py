# Path: verification/engine/checks_v2/constants/patterns.py
"""
Pattern Constants for XBRL Verification

Regex patterns and indicator lists for extracting and classifying
period, date, context, and value information from XBRL filings.

These patterns are DETECTION AIDS, not business logic.
They help identify structure without enforcing market-specific rules.

Categories:
1. Period Patterns - For extracting period info from context_id
2. Dimensional Patterns - For detecting dimensional contexts
3. Value Representation - For parsing nil/zero values
"""

# ==============================================================================
# PERIOD TYPE INDICATORS
# ==============================================================================
# Period type indicators found in context_id prefixes (case-insensitive)
# Format: (indicator, period_type) where period_type is 'duration' or 'instant'
# Order matters - more specific patterns should be tried first

PERIOD_TYPE_INDICATORS = [
    ('duration', 'duration'),    # Duration_1_1_2024_To_12_31_2024
    ('period', 'duration'),      # Period_...
    ('from', 'duration'),        # From_1_1_2024_To_12_31_2024
    ('asof', 'instant'),         # AsOf_12_31_2024
    ('instant', 'instant'),      # Instant_12_31_2024
    ('as_of', 'instant'),        # As_Of_12_31_2024
    ('at', 'instant'),           # At_12_31_2024
]


# ==============================================================================
# DATE COMPONENT PATTERNS
# ==============================================================================
# Regex fragments for matching date components in context_ids.
# These are building blocks combined for full pattern matching.
#
# NOTE: Curly braces are doubled ({{1,2}}) because these patterns are
# used with str.format() for template substitution.

DATE_COMPONENT_PATTERNS = {
    'month': r'(\d{{1,2}})',           # 1-12 or 01-12 (escaped braces for format)
    'day': r'(\d{{1,2}})',             # 1-31 or 01-31 (escaped braces for format)
    'year': r'(\d{{4}})',              # 4-digit year (escaped braces for format)
    'separator': r'[_\-\.]',           # Any date separator (underscore, hyphen, dot)
    'range_indicator': r'[_\-\.]?(?:to|through|thru)[_\-\.]?',  # Duration range separator
}


# ==============================================================================
# PERIOD EXTRACTION PATTERNS
# ==============================================================================
# Full context_id period extraction patterns.
# Format: (pattern_name, regex_template, extraction_groups)
#
# The regex_template uses placeholders substituted from DATE_COMPONENT_PATTERNS:
# - {sep}: separator pattern
# - {month}, {day}, {year}: date component patterns
# - {range}: range indicator pattern

PERIOD_EXTRACTION_PATTERNS = [
    # Duration: Duration_M_D_YYYY_To_M_D_YYYY or Duration_MM_DD_YYYY_To_MM_DD_YYYY
    (
        'duration_mdy_mdy',
        r'^(?:duration|period|from){sep}{month}{sep}{day}{sep}{year}{range}{month}{sep}{day}{sep}{year}',
        ['start_month', 'start_day', 'start_year', 'end_month', 'end_day', 'end_year']
    ),
    # Duration: Duration_YYYY-MM-DD_To_YYYY-MM-DD (ISO format)
    (
        'duration_ymd_ymd',
        r'^(?:duration|period|from){sep}{year}{sep}{month}{sep}{day}{range}{year}{sep}{month}{sep}{day}',
        ['start_year', 'start_month', 'start_day', 'end_year', 'end_month', 'end_day']
    ),
    # Instant: AsOf_M_D_YYYY or Instant_MM_DD_YYYY
    (
        'instant_mdy',
        r'^(?:asof|instant|as_of|at){sep}{month}{sep}{day}{sep}{year}',
        ['month', 'day', 'year']
    ),
    # Instant: AsOf_YYYY-MM-DD (ISO format)
    (
        'instant_ymd',
        r'^(?:asof|instant|as_of|at){sep}{year}{sep}{month}{sep}{day}',
        ['year', 'month', 'day']
    ),
    # Fallback: Extract any 4-digit year from context_id
    # NOTE: Braces escaped for str.format() compatibility
    (
        'year_only',
        r'(\d{{4}})',
        ['year']
    ),
]


# ==============================================================================
# CONTEXT ID DATE SEPARATORS
# ==============================================================================
# Separator characters used in context_id date encoding.
# Different markets and XBRL tools use different separators.

CONTEXT_ID_DATE_SEPARATORS = [
    '_',   # Underscore: Duration_1_1_2024 (most common)
    '-',   # Hyphen: Duration-1-1-2024
    '.',   # Dot: Duration.1.1.2024 (rare)
]


# ==============================================================================
# YEAR EXTRACTION PATTERN
# ==============================================================================
# Simple pattern for extracting 4-digit years as fallback

REGEX_YEAR_PATTERN = r'\d{4}'


# ==============================================================================
# DIMENSIONAL CONTEXT INDICATORS
# ==============================================================================
# Patterns to identify dimensional (non-default) contexts.
# Dimensional contexts contain axis and member identifiers, indicating
# the fact is for a specific dimensional slice (e.g., by equity component,
# by segment, by product line).
#
# Uses simple substring matching (case-insensitive):
# - 'axis' anywhere in context_id indicates a dimensional axis
# - 'member' anywhere in context_id indicates a dimensional member

DIMENSIONAL_CONTEXT_INDICATORS = [
    'axis',      # Matches *axis* - any axis indicator
    'member',    # Matches *member* - any member indicator
    'segment',   # Matches *segment* - business segment indicator
    '_class_',   # Matches class indicators (ClassAMember, etc.)
    'component', # Matches *component* - equity component indicator
]


# ==============================================================================
# CONCEPTS WITH KNOWN DIMENSIONAL VARIANTS
# ==============================================================================
# Concepts that commonly have dimensional breakdowns and should NOT be compared
# across contexts unless we have explicit dimensional information.
#
# These concepts often appear both at consolidated level AND broken down by:
# - Stock class (Class A, Class B, Preferred Series A, etc.)
# - Segment (Operating segments)
# - Component (Equity components)
#
# CRITICAL: These concepts should be EXCLUDED from vertical cross-statement
# checks unless we can confirm they're from non-dimensional contexts.

CONCEPTS_WITH_DIMENSIONAL_VARIANTS = [
    # Stock shares concepts - often reported by class
    'sharesauthorized',
    'sharesissued',
    'sharesoutstanding',
    'sharesissuedandoutstanding',
    'parvalue',
    'parorstatedvalue',
    # Stock value concepts
    'commonstockvalue',
    'preferredstockvalue',
    'treasurystock',
    # Equity component concepts
    'retainedearnings',
    'accumulatedothercomprehensiveincome',
    'additionalpaidi',  # Matches AdditionalPaidInCapital variants
    # Segment-level concepts
    'revenue',
    'operatingincome',
    'assets',
    'goodwill',
    # Intangible asset concepts - different assets have different values
    'finitelivedintangibleasset',
    'indefinitelivedintangibleasset',
    'usefullife',
    'amortization',
    # Debt instrument concepts - different instruments have different rates/terms
    'debtinstrument',
    'interestrate',
    'maturitydate',
    'faceamount',
    # Share-based compensation - different plans/awards have different values
    'sharebasedcompensation',
    'allocatedsharebasedcompensation',  # Allocated by segment/function
    'stockoption',
    'restrictestock',
    'performanceunit',
    'grantdatefairvalue',
    'vestingperiod',
    'exerciseprice',
    # Lease concepts - different leases have different terms
    'leasecost',
    'leaseliability',
    'rightofuseasset',
    'lesseeoperatinglease',  # Lessee lease terms vary by lease
    # Investment concepts - different investments have different values
    'investmentinterestrate',
    'fairvalue',
    # Defined benefit plan concepts - different asset classes/components
    'definedbenefitplan',
    'pensionplan',
    'postretirement',
    # Credit facility concepts - different facilities have different terms
    'lineofcredit',
    'creditfacility',
    'revolvingcredit',
    # Count concepts - often broken down by type/category
    'numberof',
    # Proceeds and payments - often broken down by source/use
    'proceedsfrom',
    'paymentfor',
    # Tax concepts - often broken down by jurisdiction or timing difference type
    'deferredtaxasset',
    'deferredtaxliabilit',  # Matches DeferredTaxLiabilities, DeferredTaxLiability
    'valuationallowance',
    'incometaxexpense',
    # Income/loss concepts - can appear with segment breakdowns
    'netincomeloss',
    'operatingincomeloss',
    'incomelossfromcontinuing',
    'comprehensiveincome',
]

# Pattern fragments for detecting dimensional concepts dynamically
DIMENSIONAL_CONCEPT_PATTERNS = [
    'shares',         # Any shares-related concept
    'byclass',        # Explicit class breakdown
    'bysegment',      # Explicit segment breakdown
    'bycomponent',    # Explicit component breakdown
    'byplan',         # Share-based comp by plan
    'byaward',        # Share-based comp by award type
    'byinstrument',   # Debt by instrument
    'byasset',        # By asset type
    'bylease',        # By lease
    'bycategory',     # By category
    'bytype',         # By type
    'byfacility',     # By facility
    'weightedaverage',  # Weighted averages are often by component
]


# ==============================================================================
# VALUE REPRESENTATION PATTERNS
# ==============================================================================
# Strings that represent nil/zero values in financial statements.
# Used to detect and handle nil-valued facts properly.

# Unicode characters for dash representations
EM_DASH = '\u2014'  # Em-dash character (commonly used in SEC filings)
EN_DASH = '\u2013'  # En-dash character

# Value representations that mean zero/nil
NIL_VALUES = {
    '',       # Empty string
    '-',      # Single hyphen
    '--',     # Double hyphen
    '---',    # Triple hyphen
    'nil',    # Explicit nil
    'N/A',    # Not applicable
    'n/a',    # Lowercase N/A
    'None',   # Python None as string
    'none',   # Lowercase none
}


# ==============================================================================
# SIGN PATTERN SEMANTIC DETECTION
# ==============================================================================
# Patterns for inferring sign from concept names (semantic analysis).
# Used as fallback when explicit sign information is not available.

# DEFICIT-SPECIFIC patterns for calculation verification
# These patterns identify concepts where companies typically file positive values
# but the value should semantically be negative for calculation purposes.
# IMPORTANT: These are ONLY for accumulated deficit/loss concepts, NOT general losses.
DEFICIT_SEMANTIC_PATTERNS = [
    r'AccumulatedDeficit',        # RetainedEarningsAccumulatedDeficit
    r'Deficit$',                  # Any concept ending in Deficit
    r'DeficitAccumulated',        # Alternative ordering
    r'RetainedEarnings.*Deficit', # RetainedEarningsDeficit variants
]

# Patterns suggesting negative values (cash outflows, expenses)
# WARNING: These are too broad for calculation verification - use DEFICIT_SEMANTIC_PATTERNS instead
# These patterns are designed for cash flow statement analysis, NOT equity calculations
NEGATIVE_CONCEPT_PATTERNS = [
    r'^Payments?',       # Payments, Payment
    r'^Repayments?',     # Repayments, Repayment
    r'Expense$',         # ...Expense
    r'Cost$',            # ...Cost
    r'Loss$',            # ...Loss
    r'^Decrease',        # Decrease...
    r'Outflow',          # ...Outflow...
    r'^Use[ds]?',        # Used, Uses
]

# Patterns suggesting positive values (cash inflows, revenues)
POSITIVE_CONCEPT_PATTERNS = [
    r'^Proceeds?',       # Proceeds
    r'^Revenue',         # Revenue...
    r'^Income',          # Income...
    r'^Gain',            # Gain...
    r'^Increase',        # Increase...
    r'Inflow',           # ...Inflow...
    r'^Provide[ds]?',    # Provided, Provides
]


__all__ = [
    # Period patterns
    'PERIOD_TYPE_INDICATORS',
    'DATE_COMPONENT_PATTERNS',
    'PERIOD_EXTRACTION_PATTERNS',
    'CONTEXT_ID_DATE_SEPARATORS',
    'REGEX_YEAR_PATTERN',
    # Dimensional patterns
    'DIMENSIONAL_CONTEXT_INDICATORS',
    'CONCEPTS_WITH_DIMENSIONAL_VARIANTS',
    'DIMENSIONAL_CONCEPT_PATTERNS',
    # Value representations
    'NIL_VALUES',
    'EM_DASH',
    'EN_DASH',
    # Semantic sign patterns
    'DEFICIT_SEMANTIC_PATTERNS',
    'NEGATIVE_CONCEPT_PATTERNS',
    'POSITIVE_CONCEPT_PATTERNS',
]
