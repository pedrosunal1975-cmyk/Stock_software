# Path: verification/constants.py
"""
Verification Module Constants

Module-wide constants for the verification system.
All market-agnostic constants live here.
"""

# ==============================================================================
# QUALITY LEVELS
# ==============================================================================
QUALITY_EXCELLENT = 'EXCELLENT'
QUALITY_GOOD = 'GOOD'
QUALITY_FAIR = 'FAIR'
QUALITY_POOR = 'POOR'
QUALITY_UNUSABLE = 'UNUSABLE'

QUALITY_LEVELS = [
    QUALITY_EXCELLENT,
    QUALITY_GOOD,
    QUALITY_FAIR,
    QUALITY_POOR,
    QUALITY_UNUSABLE,
]

# ==============================================================================
# CHECK TYPES
# ==============================================================================
CHECK_TYPE_HORIZONTAL = 'horizontal'
CHECK_TYPE_VERTICAL = 'vertical'
CHECK_TYPE_LIBRARY = 'library'

CHECK_TYPES = [
    CHECK_TYPE_HORIZONTAL,
    CHECK_TYPE_VERTICAL,
    CHECK_TYPE_LIBRARY,
]

# ==============================================================================
# SEVERITY LEVELS
# ==============================================================================
SEVERITY_CRITICAL = 'critical'
SEVERITY_WARNING = 'warning'
SEVERITY_INFO = 'info'

SEVERITY_LEVELS = [
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    SEVERITY_INFO,
]

# ==============================================================================
# IPO LOGGING PREFIXES
# ==============================================================================
LOG_INPUT = '[INPUT]'
LOG_PROCESS = '[PROCESS]'
LOG_OUTPUT = '[OUTPUT]'

# ==============================================================================
# FILE MARKERS AND NAMES
# ==============================================================================
# Marker files for identifying mapped statement directories
MAIN_STATEMENTS_FILE = 'MAIN_FINANCIAL_STATEMENTS.json'
STATEMENTS_JSON_FILE = 'statements.json'

# Output file names
# Single verification report based on company XBRL calculation linkbase
# Taxonomy-based verification has been removed (standard taxonomies don't contain company extensions)
REPORT_FILE = 'report.json'
SUMMARY_FILE = 'summary.txt'

# ==============================================================================
# SUPPORTED MARKETS
# ==============================================================================
MARKET_SEC = 'sec'
MARKET_ESEF = 'esef'

SUPPORTED_MARKETS = [
    MARKET_SEC,
    MARKET_ESEF,
]

# ==============================================================================
# DIRECTORY SEARCH LIMITS
# ==============================================================================
MAX_SEARCH_DEPTH = 25
MAX_FILE_SIZE_MB = 500
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# ==============================================================================
# FILE PATTERNS
# ==============================================================================
# Patterns for recognizing different file types
JSON_EXTENSIONS = ['.json']
XML_EXTENSIONS = ['.xml', '.xbrl', '.xsd']
CSV_EXTENSIONS = ['.csv']
EXCEL_EXTENSIONS = ['.xlsx', '.xlsm']

# ==============================================================================
# XBRL SPECIFICATION CONSTANTS
# ==============================================================================
# XLink namespace (XBRL 2.1 Specification)
XLINK_NAMESPACE = 'http://www.w3.org/1999/xlink'
XBRL_LINKBASE_NAMESPACE = 'http://www.xbrl.org/2003/linkbase'

# Linkbase file patterns
CALCULATION_LINKBASE_PATTERNS = ['_cal.xml', '_calculation.xml', '-cal.xml']
PRESENTATION_LINKBASE_PATTERNS = ['_pre.xml', '_presentation.xml', '-pre.xml']
DEFINITION_LINKBASE_PATTERNS = ['_def.xml', '_definition.xml', '-def.xml']
LABEL_LINKBASE_PATTERNS = ['_lab.xml', '_label.xml', '-lab.xml']


__all__ = [
    # Quality levels
    'QUALITY_EXCELLENT',
    'QUALITY_GOOD',
    'QUALITY_FAIR',
    'QUALITY_POOR',
    'QUALITY_UNUSABLE',
    'QUALITY_LEVELS',

    # Check types
    'CHECK_TYPE_HORIZONTAL',
    'CHECK_TYPE_VERTICAL',
    'CHECK_TYPE_LIBRARY',
    'CHECK_TYPES',

    # Severity levels
    'SEVERITY_CRITICAL',
    'SEVERITY_WARNING',
    'SEVERITY_INFO',
    'SEVERITY_LEVELS',

    # IPO logging
    'LOG_INPUT',
    'LOG_PROCESS',
    'LOG_OUTPUT',

    # File markers
    'MAIN_STATEMENTS_FILE',
    'STATEMENTS_JSON_FILE',
    'REPORT_FILE',
    'SUMMARY_FILE',

    # Markets
    'MARKET_SEC',
    'MARKET_ESEF',
    'SUPPORTED_MARKETS',

    # Search limits
    'MAX_SEARCH_DEPTH',
    'MAX_FILE_SIZE_MB',
    'MAX_FILE_SIZE_BYTES',

    # File patterns
    'JSON_EXTENSIONS',
    'XML_EXTENSIONS',
    'CSV_EXTENSIONS',
    'EXCEL_EXTENSIONS',

    # XBRL constants
    'XLINK_NAMESPACE',
    'XBRL_LINKBASE_NAMESPACE',
    'CALCULATION_LINKBASE_PATTERNS',
    'PRESENTATION_LINKBASE_PATTERNS',
    'DEFINITION_LINKBASE_PATTERNS',
    'LABEL_LINKBASE_PATTERNS',
]
